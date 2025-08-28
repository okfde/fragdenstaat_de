import decimal
import uuid
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.postgres.fields import HStoreField
from django.core.exceptions import ValidationError
from django.db import connection, models
from django.db.models.functions import RowNumber
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format, number_format
from django.utils.functional import cached_property
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy, pgettext

from cms.models.pluginmodel import CMSPlugin
from dateutil.relativedelta import relativedelta
from django_countries.fields import CountryField
from djangocms_frontend.fields import AttributesField
from froide_payment.models import (
    CHECKOUT_PAYMENT_CHOICES_DICT,
    Order,
    Payment,
    PaymentStatus,
    Subscription,
)
from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase

from froide.helper.spam import suspicious_ip

from fragdenstaat_de.fds_newsletter.models import Subscriber

QUICKPAYMENT_METHOD = "creditcard"
PAYMENT_METHOD_LIST = ("sepa", "paypal", "banktransfer", QUICKPAYMENT_METHOD)
MIN_AMOUNT = 5
MAX_AMOUNT = 10000
PAYMENT_METHOD_MAX_AMOUNT = {"sepa": decimal.Decimal(5000)}

PAYMENT_METHODS = [
    (method, CHECKOUT_PAYMENT_CHOICES_DICT[method]) for method in PAYMENT_METHOD_LIST
]
PAYMENT_METHODS_DICT = dict(PAYMENT_METHODS)


ONCE = "once"
RECURRING = "recurring"
ONCE_RECURRING = "once_recurring"

INTERVAL_SETTINGS_CHOICES = [
    (ONCE, _("Only once")),
    (RECURRING, _("Only recurring")),
    (ONCE_RECURRING, _("Both")),
]
INTERVAL_CHOICES = [
    (0, _("once")),
    (1, _("monthly")),
    (3, _("quarterly")),
    (12, _("yearly")),
]
RECURRING_INTERVAL_CHOICES = INTERVAL_CHOICES[1:] + [
    (6, _("every six months")),
]

SALUTATION_CHOICES = (
    ("", pgettext("salutation neutral", "Hello")),
    ("formal", pgettext("salutation formal", "Good day")),
    ("formal_f", pgettext("salutation female formal", "Dear Ms.")),
    ("formal_m", pgettext("salutation male formal", "Dear Mr.")),
    ("informal_f", pgettext("salutation female informal", "Dear")),
    ("informal_m", pgettext("salutation male informal", "Dear")),
    ("informal_n", pgettext("salutation neutral informal", "Dear")),
)
SALUTATION_DICT = dict(SALUTATION_CHOICES)


DONATION_PROJECTS = getattr(settings, "DONATION_PROJECTS", [("", _("Default"))])
DEFAULT_DONATION_PROJECT = DONATION_PROJECTS[0][0]


class DonorTag(TagBase):
    class Meta:
        verbose_name = _("Donor Tag")
        verbose_name_plural = _("Donor Tags")


class TaggedDonor(TaggedItemBase):
    tag = models.ForeignKey(DonorTag, related_name="donors", on_delete=models.CASCADE)
    content_object = models.ForeignKey("Donor", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Tagged Donor")
        verbose_name_plural = _("Tagged Donors")


class Donor(models.Model):
    salutation = models.CharField(max_length=25, blank=True, choices=SALUTATION_CHOICES)
    first_name = models.CharField(max_length=256, blank=True)
    last_name = models.CharField(max_length=256, blank=True)
    company_name = models.CharField(max_length=256, blank=True)
    address = models.CharField(max_length=256, blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=256, blank=True)
    country = CountryField(blank=True)

    email = models.EmailField(blank=True, default="")
    identifier = models.CharField(blank=True, max_length=256)
    attributes = HStoreField(null=True, blank=True)

    active = models.BooleanField(default=False)
    first_donation = models.DateTimeField(default=timezone.now)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    subscriptions = models.ManyToManyField(Subscription, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    email_confirmation_sent = models.DateTimeField(null=True, blank=True)
    email_confirmed = models.DateTimeField(null=True, blank=True)

    contact_allowed = models.BooleanField(null=True, default=None)
    become_user = models.BooleanField(null=True, default=None)
    receipt = models.BooleanField(null=True, default=None)

    subscriber = models.ForeignKey(
        Subscriber, null=True, blank=True, on_delete=models.SET_NULL
    )

    recurring_amount = models.DecimalField(
        max_digits=12, decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=0
    )
    invalid = models.BooleanField(default=False)
    duplicate = models.UUIDField(editable=False, null=True, blank=True)

    note = models.TextField(blank=True)
    tags = TaggableManager(through=TaggedDonor, blank=True)

    class Meta:
        ordering = ("-id",)
        get_latest_by = "first_donation"
        verbose_name = _("donor")
        verbose_name_plural = _("donors")

    def __str__(self):
        return "{} ({})".format(self.get_full_name(), self.email)

    def get_full_name(self):
        name = "{} {}".format(self.first_name, self.last_name).strip()
        if self.company_name and not name:
            return self.company_name
        return name

    def get_company_name_or_name(self):
        if self.company_name:
            return self.company_name
        return self.get_full_name()

    def get_german_salutation(self):
        if self.company_name and (not self.first_name or not self.last_name):
            return "Guten Tag"
        return self.get_salutation()

    def get_complete_name(self):
        name = "{} {}".format(self.first_name, self.last_name).strip()
        if self.company_name:
            if not name:
                return self.company_name
            return "%s (%s)" % (name, self.company_name)
        return name

    def get_order_name(self):
        name = "{} {}".format(self.last_name, self.first_name).strip()
        if self.company_name and not name:
            return self.company_name
        return name

    def get_salutation(self):
        salutation = SALUTATION_DICT.get(self.salutation, None)
        if salutation is None:
            salutation = self.salutation
        if "informal_" in self.salutation:
            name = self.first_name
        elif "formal_" in self.salutation:
            name = self.last_name
        else:
            name = self.get_full_name()
        return "{} {}".format(salutation, name)

    def get_full_address(self):
        return "\n".join(
            x
            for x in [
                self.address,
                "{} {}".format(self.postcode, self.city),
                self.country.name,
            ]
            if x
        )

    def get_absolute_url(self):
        return reverse("fds_donation:donor", kwargs={"token": str(self.uuid)})

    def get_absolute_change_url(self):
        return reverse("fds_donation:donor-change", kwargs={"token": str(self.uuid)})

    def get_absolute_donate_url(self):
        return reverse("fds_donation:donor-donate", kwargs={"token": str(self.uuid)})

    def get_url(self):
        return settings.SITE_URL + self.get_absolute_url()

    def get_donate_url(self):
        return settings.SITE_URL + self.get_absolute_donate_url()

    def get_change_url(self):
        return settings.SITE_URL + self.get_absolute_donate_url()

    @property
    def tag_list(self):
        return ", ".join(o.name for o in self.tags.all())

    def has_active_subscription(self):
        return self.subscriptions.filter(canceled__isnull=False).exists()

    def get_form_data(self):
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "company_name": self.company_name,
            "address": self.address,
            "city": self.city,
            "postcode": self.postcode,
            "country": self.country,
        }

    @cached_property
    def last_donation(self):
        return self.donations.filter(received_timestamp__isnull=False).aggregate(
            last_donation=models.Max("timestamp")
        )["last_donation"]

    def calculate_recurring_amount(self):
        """
        Calculate the total recurring amount for this donor.
        """
        return self.recurrences.filter(cancel_date__isnull=True).aggregate(
            total=models.Sum(models.F("amount") / models.F("interval"))
        )["total"] or decimal.Decimal("0.00")

    def get_recurrence_streak_start_date(self):
        """
        Returns the start date of the current recurrence streak.
        If there are no recurrences, returns None.
        """
        recurrences = self.recurrences.all().order_by("start_date")
        if not recurrences:
            return None
        first_recurrence = recurrences[0]
        if first_recurrence.cancel_date is None:
            # If the first recurrence is still active, we can use its start date
            return first_recurrence.start_date
        if len(recurrences) == 1:
            return None

        start_date = first_recurrence.start_date
        last_date = first_recurrence.cancel_date
        last_interval = first_recurrence.interval

        for recurrence in recurrences[1:]:
            delta = recurrence.start_date - last_date
            if delta > timedelta(days=int(31 * (last_interval * 1.5))):
                start_date = recurrence.start_date
            if recurrence.cancel_date is None:
                return start_date
            last_date = recurrence.cancel_date
            last_interval = recurrence.interval

        return None

    @cached_property
    def recently_donated(self):
        recently_donated = False
        if self.last_donation:
            year = timedelta(days=365)
            recently_donated = timezone.now() - self.last_donation <= year
        return recently_donated

    @property
    def is_eligible_for_gift(self):
        return self.recurring_amount >= 10

    def incomplete_donations(self):
        """
        Returns donations that are not completed yet.
        """
        return self.donations.filter(completed=False)

    def last_incomplete_donation(self):
        """
        Returns donations that are not completed yet.
        """
        return self.incomplete_donations().order_by("-timestamp").first()

    def get_email_context(self):
        context = {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "name": self.get_full_name(),
            "email": self.email,
            "company_name": self.company_name,
            "salutation": self.get_salutation(),
            "address": self.get_full_address(),
            "donor_url": self.get_url(),
        }

        if self.user:
            context["donor_url"] = settings.SITE_URL + self.user.get_autologin_url(
                reverse("fds_donation:donor-user")
            )
        else:
            context["donor_url"] = self.get_url()

        last_year = timezone.now().year - 1
        donations = Donation.objects.filter(
            donor=self, received_timestamp__isnull=False
        )
        aggregate = donations.aggregate(
            amount_total=models.Sum("amount"),
            amount_last_year=models.Sum(
                "amount", filter=models.Q(received_timestamp__year=last_year)
            ),
        )

        context.update(
            {
                "amount_total": aggregate["amount_total"],
                "amount_last_year": aggregate["amount_last_year"],
                "last_year": last_year,
                "donations": donations,
            }
        )

        return context


def update_donation_numbers(donor_id):
    donations = Donation.objects.filter(donor_id=donor_id, completed=True).annotate(
        new_number=models.Window(
            expression=RowNumber(),
            order_by=models.F("timestamp").asc(),
        )
    )
    # Can't call .update() directly due to Django
    # ORM limitations, loop and update:
    for d in donations:
        if d.number != d.new_number:
            Donation.objects.filter(id=d.id).update(number=d.new_number)


def get_project_choices():
    return DONATION_PROJECTS


class RecurrenceManager(models.Manager):
    def cleanup(self):
        return (
            self.get_queryset()
            .annotate(donation_count=models.Count("donations", distinct=True))
            .filter(donation_count=0)
            .delete()
        )


class CancelReason(models.TextChoices):
    NO_REASON = "", _("No reason given")
    FINANCIAL = "financial", _("Financial reasons")
    UNINTENDED = "unintended", _("Mistakenly set up, do not remember doing so")
    LOST = "lost", _("I do not want to support this project anymore")
    OTHER = "other", _("Other")


def get_recurring_interval_choices():
    return RECURRING_INTERVAL_CHOICES


class Recurrence(models.Model):
    donor = models.ForeignKey(
        Donor,
        null=True,
        blank=True,
        related_name="recurrences",
        on_delete=models.CASCADE,
    )
    subscription = models.OneToOneField(
        Subscription,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    active = models.BooleanField(default=True)
    project = models.CharField(
        max_length=40,
        default=DEFAULT_DONATION_PROJECT,
        choices=get_project_choices,
    )
    method = models.CharField(max_length=256, blank=True)
    start_date = models.DateTimeField()
    interval = models.IntegerField(choices=get_recurring_interval_choices)
    amount = models.DecimalField(
        max_digits=12, decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=0
    )
    cancel_date = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text=_("Reason for cancellation"),
        choices=CancelReason,
    )
    cancel_feedback = models.TextField(blank=True)

    objects = RecurrenceManager()

    class Meta:
        verbose_name = _("Recurring donation")
        verbose_name_plural = _("Recurring donations")

    def __str__(self):
        return "{donor}: {desc}".format(donor=self.donor, desc=self.get_description())

    def get_description(self):
        return ngettext_lazy(
            "{amount} EUR every month via {method} since {start}.",
            "{amount} EUR every {interval} months via {method} since {start}.",
            self.interval,
        ).format(
            donor=self.donor,
            amount=number_format(self.amount),
            interval=self.interval,
            method=PAYMENT_METHODS_DICT.get(self.method, self.method),
            start=date_format(self.start_date, "SHORT_DATE_FORMAT"),
        ) + (
            " ({})".format(
                _("canceled on {}").format(
                    date_format(self.cancel_date, "SHORT_DATE_FORMAT")
                )
            )
            if self.cancel_date
            else ""
        )

    @property
    def is_banktransfer(self):
        return self.method == "banktransfer"

    @property
    def is_paypal(self):
        return self.method == "paypal"

    def sum_amount(self):
        return Donation.objects.filter(recurrence=self).aggregate(
            total_amount=models.Sum("amount")
        )["total_amount"] or decimal.Decimal("0.00")

    def days(self):
        last_date = timezone.now()
        if self.cancel_date:
            last_date = self.cancel_date
        return (last_date - self.start_date).days

    def next_expected_date(self) -> datetime | None:
        """
        Returns the next expected date for this recurring pattern.
        If canceled, returns None.
        """
        if self.canceled:
            return None

        interval = relativedelta(months=self.interval)

        last_received_donation = (
            self.donations.filter(received_timestamp__isnull=False)
            .order_by("-received_timestamp")
            .first()
        )
        if last_received_donation:
            last_received_timestamp = last_received_donation.received_timestamp
        else:
            # must be coming in any time now
            last_received_timestamp = timezone.now()
        return last_received_timestamp + interval

    def first_donation(self):
        """
        Returns the first donation for this recurrence.
        If no donations exist, returns None.
        """
        return self.donations.order_by("timestamp").first()


class DonationManager(models.Manager):
    def estimate_received_donations(self, start_date: date):
        today = timezone.now().date()
        SEPA_TIME = timedelta(days=7)
        BANKTRANSFER_TIME = timedelta(days=35)
        return (
            self.get_queryset()
            .filter(
                completed=True,
                timestamp__gte=start_date,
            )
            .filter(
                models.Q(payment__isnull=True)
                | ~models.Q(
                    payment__status__in=[
                        PaymentStatus.REFUNDED,
                        PaymentStatus.REJECTED,
                        PaymentStatus.ERROR,
                        PaymentStatus.CANCELED,
                        PaymentStatus.DEFERRED,
                    ]
                )
            )
            .filter(
                models.Q(
                    received_timestamp__isnull=False,
                    method__in=["paypal", "creditcard"],
                )
                | models.Q(
                    method__in=["sepa", "sofort"], timestamp__gte=today - SEPA_TIME
                )
                | models.Q(
                    method__in=["sepa", "sofort"],
                    timestamp__lt=today - SEPA_TIME,
                    received_timestamp__isnull=False,
                )
                | models.Q(
                    method__in=["banktransfer"],
                    timestamp__gte=today - BANKTRANSFER_TIME,
                )
                | models.Q(
                    method__in=["banktransfer"],
                    timestamp__lt=today - BANKTRANSFER_TIME,
                    received_timestamp__isnull=False,
                )
            )
        )


class Donation(models.Model):
    donor = models.ForeignKey(
        Donor,
        null=True,
        blank=True,
        related_name="donations",
        on_delete=models.SET_NULL,
    )
    timestamp = models.DateTimeField(default=timezone.now)
    completed = models.BooleanField(default=False)
    amount = models.DecimalField(
        max_digits=12, decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=0
    )
    amount_received = models.DecimalField(
        max_digits=12, decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=0
    )
    received_timestamp = models.DateTimeField(blank=True, null=True)
    email_sent = models.DateTimeField(null=True, blank=True)
    number = models.IntegerField(default=0)

    note = models.TextField(blank=True)

    method = models.CharField(max_length=256, blank=True)
    identifier = models.CharField(max_length=1024, blank=True)
    purpose = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=1024, blank=True)
    keyword = models.CharField(max_length=1024, blank=True)
    form_url = models.CharField(max_length=1024, blank=True)
    data = models.JSONField(blank=True, default=dict)

    export_date = models.DateTimeField(null=True, blank=True)
    receipt_date = models.DateTimeField(null=True, blank=True)

    order = models.OneToOneField(
        Order, null=True, blank=True, on_delete=models.SET_NULL
    )
    payment = models.OneToOneField(
        Payment, null=True, blank=True, on_delete=models.SET_NULL
    )
    first_recurring = models.BooleanField(default=False)
    recurring = models.BooleanField(default=False)
    recurrence = models.ForeignKey(
        Recurrence,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="donations",
    )

    project = models.CharField(
        max_length=40,
        default=DEFAULT_DONATION_PROJECT,
        choices=get_project_choices,
    )

    extra_action_url = models.CharField(max_length=255, blank=True)
    extra_action_label = models.TextField(blank=True)

    objects = DonationManager()

    class Meta:
        ordering = ("-timestamp",)
        get_latest_by = "timestamp"
        verbose_name = _("donation")
        verbose_name_plural = _("donations")

    def __str__(self):
        return "{} ({} - {})".format(self.amount, self.timestamp, self.donor)

    def save(self, *args, **kwargs):
        ret = super().save(*args, **kwargs)

        update_donation_numbers(self.donor_id)

        return ret

    def get_success_url_query(self):
        query = {
            "email": self.donor.email.encode("utf-8"),
            "amount": str(self.amount).encode("utf-8"),
        }
        if self.donor.receipt:
            query.update({"receipt": "1"})
        if self.order:
            query.update(
                {
                    "order": self.order.get_absolute_url().encode("utf-8"),
                }
            )
            if self.order.subscription:
                sub_url = self.order.subscription.get_absolute_url()
                query.update({"subscription": sub_url.encode("utf-8")})
        return urlencode(query)

    def get_success_url(self):
        if self.extra_action_url and not self.extra_action_label:
            url = self.extra_action_url
            query = self.get_success_url_query()
            return "%s?%s" % (url, query)
        if self.donor and self.donor.user:
            return self.donor.get_absolute_url() + "?complete"
        if self.donor:
            url = reverse("fds_donation:donate-complete")
            query = self.get_success_url_query()
            return "%s?%s" % (url, query)
        if self.order:
            return self.order.get_absolute_url()
        return "/"

    def get_failure_url(self):
        return reverse("fds_donation:donate-failed")

    def get_method_display(self):
        """
        Returns a human-readable display of the payment method.
        If the method is not recognized, it returns the method itself.
        """
        return CHECKOUT_PAYMENT_CHOICES_DICT.get(self.method, self.method)


class DefaultDonationManager(DonationManager):
    def get_queryset(self):
        return super().get_queryset().filter(project=DEFAULT_DONATION_PROJECT)


class DefaultDonation(Donation):
    objects = DefaultDonationManager()

    class Meta:
        proxy = True
        verbose_name = "FragDenStaat Spenden"
        verbose_name_plural = "FragDenStaat Spenden"


class DeferredDonation(Donation):
    class Meta:
        proxy = True
        verbose_name = _("Deferred Donation")
        verbose_name_plural = _("Deferred Donation")


class DonationGiftManager(models.Manager):
    def available(self):
        return (
            super()
            .get_queryset()
            .annotate(order_count=models.Count("donationgiftorder"))
            .filter(
                models.Q(inventory__isnull=True)
                | models.Q(inventory__gt=models.F("order_count"))
            )
        )


class DonationGift(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category_slug = models.SlugField(max_length=255, blank=True)
    inventory = models.PositiveIntegerField(blank=True, default=None, null=True)

    order = models.PositiveIntegerField(default=0)

    objects = DonationGiftManager()

    class Meta:
        verbose_name = _("donation gift")
        verbose_name_plural = _("donation gifts")
        ordering = (
            "order",
            "name",
        )

    def __str__(self):
        return self.name

    def has_remaining_available_to_order(self) -> bool:
        if self.inventory is None:
            return True
        return (
            self.inventory
            - DonationGiftOrder.objects.filter(donation_gift=self).count()
        ) > 0


class DonationGiftOrder(models.Model):
    donation = models.OneToOneField(
        Donation, null=True, blank=True, on_delete=models.SET_NULL
    )
    donation_gift = models.ForeignKey(DonationGift, on_delete=models.CASCADE)

    timestamp = models.DateTimeField(default=timezone.now)

    first_name = models.CharField(max_length=256, blank=True)
    last_name = models.CharField(max_length=256, blank=True)
    company_name = models.CharField(max_length=256, blank=True)
    address = models.CharField(max_length=256, blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=256, blank=True)
    country = CountryField(blank=True)

    email = models.EmailField(blank=True, default="")

    note = models.TextField(blank=True)

    shipped = models.DateTimeField(null=True, blank=True)
    tracking = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = _("donation gift order")
        verbose_name_plural = _("donation gift orders")
        ordering = ("-timestamp",)

    def __str__(self):
        return "{} {} - {} ({})".format(
            self.first_name, self.last_name, self.donation_gift, self.timestamp
        )

    def get_full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    def formatted_address(self):
        company = ""
        if self.company_name:
            company = "\n{}".format(self.company_name)
        return "{full_name}{company}\n{address}\n{postcode} {city}\n{country}".format(
            full_name=self.get_full_name(),
            company=company,
            address=self.address,
            postcode=self.postcode,
            city=self.city,
            country=self.country,
        )


class DonationGiftFormCMSPlugin(CMSPlugin):
    category = models.SlugField()
    next_url = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return str(self.category)


def validate_allowed_host_and_scheme(value):
    if not url_has_allowed_host_and_scheme(
        value, allowed_hosts=settings.ALLOWED_REDIRECT_HOSTS
    ):
        raise ValidationError("Not a valid url")


QUICKPAYMENT_CHOICES = [
    ("", _("No quick payment")),
    ("show", _("Show quick payment options")),
    ("only", _("Only quick payment options")),
]


class DonationFormCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    interval = models.CharField(max_length=20, choices=INTERVAL_SETTINGS_CHOICES)
    interval_choices = models.CharField(max_length=255, blank=True)
    amount_presets = models.CharField(max_length=255, blank=True)
    initial_amount = models.IntegerField(null=True, blank=True)
    initial_interval = models.IntegerField(null=True, blank=True)
    min_amount = models.IntegerField(null=True, blank=True)
    payment_methods = models.CharField(blank=True)

    reference = models.CharField(blank=True, max_length=255)
    keyword = models.CharField(blank=True, max_length=255)
    purpose = models.CharField(blank=True, max_length=255)
    collapsed = models.BooleanField(default=False)
    hide_contact = models.BooleanField(default=False)
    hide_account = models.BooleanField(default=False)
    quick_payment = models.CharField(
        blank=True, max_length=20, choices=QUICKPAYMENT_CHOICES
    )
    extra_classes = models.CharField(max_length=255, blank=True)

    gift_options = models.ManyToManyField(DonationGift, blank=True)
    default_gift = models.ForeignKey(
        DonationGift,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="donation_plugin_with_default",
    )

    form_action = models.CharField(max_length=255, blank=True)
    next_url = models.CharField(
        max_length=255, blank=True, validators=[validate_allowed_host_and_scheme]
    )
    next_label = models.CharField(max_length=255, blank=True)

    open_in_new_tab = models.BooleanField(default=False)

    def __str__(self):
        return "{title}: {interval} {amount_presets}".format(
            title=self.title, interval=self.interval, amount_presets=self.amount_presets
        )

    def copy_relations(self, old_instance):
        """
        Duplicate ManyToMany relations on plugin copy
        """
        self.gift_options.set(old_instance.gift_options.all())

    def make_form(self, **kwargs):
        from .form_settings import DonationFormFactory, DonationSettingsForm

        request = kwargs["request"]
        reference = kwargs.pop("reference", "")
        keyword = kwargs.pop("keyword", "")

        plugin_data = {
            "title": self.title,
            "interval": self.interval,
            "interval_choices": self.interval_choices,
            "amount_presets": self.amount_presets,
            "initial_amount": self.initial_amount or "",
            "initial_interval": self.initial_interval or "",
            "min_amount": self.min_amount,
            "reference": self.reference or reference,
            "keyword": self.keyword or keyword,
            "purpose": self.purpose,
            "payment_methods": self.payment_methods or "",
            "hide_contact": self.hide_contact,
            "hide_account": self.hide_account,
            "collapsed": self.collapsed,
            "gift_options": [gift.id for gift in self.gift_options.all()],
            "default_gift": self.default_gift_id,
            "next_url": self.next_url,
            "next_label": self.next_label,
            "quick_payment": self.quick_payment,
        }
        request_data = DonationFormFactory.from_request(request)
        plugin_data.update(request_data)

        if request.GET.get("initial_amount"):
            plugin_data["collapsed"] = False

        form = DonationSettingsForm(data=plugin_data)
        return form.make_donation_form(**kwargs)


class DonationProgressBarCMSPlugin(CMSPlugin):
    start_date = models.DateTimeField()
    reached_goal = models.DecimalField(
        decimal_places=2, max_digits=10, blank=True, null=True
    )
    received_donations_only = models.BooleanField(default=False)
    white_text = models.BooleanField(default=False)
    donation_goal = models.DecimalField(decimal_places=2, max_digits=10)
    purpose = models.CharField(blank=True)


class EmailDonationButtonCMSPlugin(CMSPlugin):
    interval = models.CharField(max_length=20, choices=INTERVAL_SETTINGS_CHOICES)
    amount_presets = models.CharField(max_length=255, blank=True)
    initial_amount = models.IntegerField(null=True, blank=True)
    initial_interval = models.IntegerField(null=True, blank=True)
    min_amount = models.IntegerField(default=0)

    action_url = models.CharField(max_length=255, blank=True)
    action_label = models.CharField(max_length=255, blank=True)
    attributes = AttributesField()

    context_vars = ["action_url", "action_label"]

    empty_vars = set()

    def __str__(self):
        return str(self.action_label)

    def get_context(self):
        action_url = self.action_url
        if not action_url:
            action_url = reverse("fds_donation:donate")
        if "?" in action_url:
            action_url += "&"
        else:
            action_url += "?"

        action_url += urlencode(
            {
                "amount_presets": self.amount_presets,
                "initial_amount": str(self.initial_amount)
                if self.initial_amount is not None
                else "",
                "initial_interval": str(self.initial_interval)
                if self.initial_interval is not None
                else "",
                "interval": str(self.interval),
                "min_amount": str(self.min_amount),
                "pk_placement": f"donationbutton-{self.pk}",
            }
        )
        return {
            "action_label": self.action_label,
            "action_url": action_url,
        }


class DonationFormViewCountManager(models.Manager):
    def handle_request(self, request):
        if request.user.is_staff:
            return
        reference = request.GET.get("pk_campaign", "")
        if suspicious_ip(request) is not None:
            return
        self.increment(request.path, reference)

    def increment(self, path, reference):
        """
        Uses raw SQL to increment the view count for a given path and reference.
        Django update_or_create does not support incrementing a field in the same way and would require two queries.
        https://code.djangoproject.com/ticket/25195
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO fds_donation_donationformviewcount(path, reference, date, count, last_updated) VALUES (%s, %s, now(), 1, now())
                ON CONFLICT (path, reference, date) DO UPDATE SET count = fds_donation_donationformviewcount.count + 1, last_updated = now();
            """,
                [path, reference],
            )


class DonationFormViewCount(models.Model):
    path = models.CharField(max_length=255)
    reference = models.CharField(max_length=255, blank=True)
    date = models.DateField(default=timezone.now)
    count = models.PositiveBigIntegerField(default=0)
    last_updated = models.DateTimeField(default=timezone.now)

    objects = DonationFormViewCountManager()

    def __str__(self):
        return f"{self.reference}: {self.count} ({self.last_updated})"

    class Meta:
        verbose_name = _("Donation Form View Count")
        verbose_name_plural = _("Donation Form View Counts")
        ordering = ("-last_updated",)
        indexes = [
            models.Index(fields=["path", "reference", "date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["path", "reference", "date"], name="unique_path_ref"
            )
        ]
