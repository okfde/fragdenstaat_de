import uuid
from datetime import date, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.postgres.fields import HStoreField
from django.db import models
from django.db.models.functions import RowNumber
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext

from cms.models.pluginmodel import CMSPlugin
from django_countries.fields import CountryField
from fragdenstaat_de.fds_newsletter.models import Subscriber
from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase

from froide_payment.models import Order, Payment, PaymentStatus, Subscription

INTERVAL_SETTINGS_CHOICES = [
    ("once", _("Only once")),
    ("recurring", _("Only recurring")),
    ("once_recurring", _("Both")),
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
    contact_allowed = models.BooleanField(default=False)
    become_user = models.BooleanField(default=False)
    receipt = models.BooleanField(default=False)

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
    reference = models.CharField(max_length=255, blank=True)
    keyword = models.CharField(max_length=255, blank=True)

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
    project = models.CharField(
        max_length=40,
        default=DEFAULT_DONATION_PROJECT,
        choices=DONATION_PROJECTS,
    )

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

    def get_success_url(self):
        if self.donor and self.donor.user:
            return self.donor.get_absolute_url() + "?complete"
        if self.donor:
            url = reverse("fds_donation:donate-complete")
            query = {
                "email": self.donor.email.encode("utf-8"),
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
            query = urlencode(query)
            return "%s?%s" % (url, query)
        if self.order:
            return self.order.get_absolute_url()
        return "/"

    def get_failure_url(self):
        return reverse("fds_donation:donate-failed")


class DefaultDonationManager(DonationManager):
    def get_queryset(self):
        return super().get_queryset().filter(project=DEFAULT_DONATION_PROJECT)


class DefaultDonation(Donation):
    objects = DefaultDonationManager()

    class Meta:
        proxy = True
        verbose_name = "FragDenStaat Spenden"
        verbose_name_plural = "FragDenStaat Spenden"


class DonationGift(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category_slug = models.SlugField(max_length=255, blank=True)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("donation gift")
        verbose_name_plural = _("donation gifts")
        ordering = (
            "order",
            "name",
        )

    def __str__(self):
        return self.name


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
        ordering = ("timestamp",)

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


class DonationFormCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    interval = models.CharField(max_length=20, choices=INTERVAL_SETTINGS_CHOICES)
    amount_presets = models.CharField(max_length=255, blank=True)
    initial_amount = models.IntegerField(null=True, blank=True)
    initial_interval = models.IntegerField(null=True, blank=True)
    min_amount = models.IntegerField(null=True, blank=True)

    reference = models.CharField(blank=True, max_length=255)
    keyword = models.CharField(blank=True, max_length=255)
    purpose = models.CharField(blank=True, max_length=255)
    collapsed = models.BooleanField(default=False)
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
    next_url = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return "{interval} {amount_presets}".format(
            interval=self.interval, amount_presets=self.amount_presets
        )

    def copy_relations(self, old_instance):
        """
        Duplicate ManyToMany relations on plugin copy
        """
        self.gift_options.set(old_instance.gift_options.all())

    def make_form(self, **kwargs):
        from .forms import DonationSettingsForm

        reference = kwargs.pop("reference", "")
        keyword = kwargs.pop("keyword", "")

        form = DonationSettingsForm(
            data={
                "title": self.title,
                "interval": self.interval,
                "amount_presets": self.amount_presets,
                "initial_amount": self.initial_amount,
                "initial_interval": self.initial_interval,
                "min_amount": self.min_amount,
                "reference": self.reference or reference,
                "keyword": self.keyword or keyword,
                "purpose": self.purpose,
                "collapsed": self.collapsed,
                "gift_options": [gift.id for gift in self.gift_options.all()],
                "default_gift": self.default_gift_id,
            }
        )
        return form.make_donation_form(**kwargs)


class DonationProgressBarCMSPlugin(CMSPlugin):
    start_date = models.DateTimeField()
    reached_goal = models.DecimalField(
        decimal_places=2, max_digits=10, blank=True, null=True
    )
    received_donations_only = models.BooleanField(default=False)
    white_text = models.BooleanField(default=False)
    donation_goal = models.DecimalField(decimal_places=2, max_digits=10)
