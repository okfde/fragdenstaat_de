import logging
from typing import cast, override
from urllib.parse import parse_qsl

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.mail import mail_managers
from django.core.validators import MinValueValidator
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from froide_payment.forms import StartPaymentMixin
from froide_payment.utils import interval_description

from froide.account.utils import parse_address
from froide.helper.content_urls import get_content_url
from froide.helper.spam import SpamProtectionMixin
from froide.helper.widgets import (
    BootstrapRadioSelect,
    BootstrapSelect,
    InlineBootstrapRadioSelect,
)

from .form_settings import DonationFormFactory
from .models import (
    CHECKOUT_PAYMENT_CHOICES_DICT,
    DEFAULT_DONATION_PROJECT,
    INTERVAL_CHOICES,
    MIN_AMOUNT,
    ONCE,
    ONCE_RECURRING,
    PAYMENT_METHOD_MAX_AMOUNT,
    PAYMENT_METHODS,
    QUICKPAYMENT_METHOD,
    RECURRING,
    SALUTATION_CHOICES,
    CancelReason,
    Donation,
    DonationGift,
    DonationGiftOrder,
    Donor,
    Recurrence,
)
from .services import get_or_create_donor
from .utils import MERGE_DONOR_FIELDS
from .validators import validate_not_too_many_uppercase
from .widgets import AmountInput

logger = logging.getLogger(__name__)


DEFAULT_PURPOSE = _("General donation")


class BasicDonationForm(StartPaymentMixin, forms.Form):
    amount = forms.DecimalField(
        localize=True,
        required=True,
        initial=None,
        min_value=MIN_AMOUNT,
        max_digits=19,
        decimal_places=2,
        label=_("Donation amount:"),
        widget=AmountInput(
            attrs={
                "title": _("Amount in Euro, comma as decimal separator"),
                "class": "text-end",
            },
            presets=[],
        ),
    )
    interval = forms.TypedChoiceField(
        choices=[],
        coerce=int,
        empty_value=None,
        required=True,
        label=_("Frequency"),
        widget=InlineBootstrapRadioSelect,
    )
    purpose = forms.ChoiceField(
        required=False,
        label=_("Donation purpose"),
        choices=[
            (DEFAULT_PURPOSE, DEFAULT_PURPOSE),
        ],
        widget=BootstrapSelect(
            attrs={"data-toggle": "nonrecurring"},
        ),
    )
    reference = forms.CharField(required=False, widget=forms.HiddenInput())
    keyword = forms.CharField(required=False, widget=forms.HiddenInput())
    form_url = forms.CharField(required=False, widget=forms.HiddenInput())
    query_params = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.action = kwargs.pop("action", None)

        user = kwargs.pop("user", None)
        if user is None or not user.is_authenticated:
            user = None
        self.user = user
        self.settings = kwargs.pop("form_settings", DonationFormFactory.default)

        if not hasattr(self, "request"):
            self.request = kwargs.pop("request", None)
        kwargs.pop("request", None)

        super().__init__(*args, **kwargs)

        self.quick_payment = False
        self.quick_payment_only = False
        if self.settings["quick_payment"] == "show":
            self.quick_payment = True
        elif self.settings["quick_payment"] == "only":
            self.quick_payment_only = True

        if hasattr(self, "request"):
            self.fields["form_url"].initial = self.request.path
            self.fields["query_params"].initial = self.request.GET.urlencode()

        if self.settings["min_amount"] and self.settings["min_amount"] >= MIN_AMOUNT:
            self.fields["amount"].min_value = self.settings["min_amount"]
            self.fields["amount"].validators.append(
                MinValueValidator(self.settings["min_amount"])
            )

        interval_choices = self.get_interval_choices()
        self.fields["interval"].choices = interval_choices

        show_purpose = self.settings["interval"] != RECURRING
        if len(interval_choices) == 1:
            show_purpose = interval_choices[0][0] == 0
            self.fields["interval"].initial = interval_choices[0][0]
            self.fields["interval"].widget = forms.HiddenInput()
            if interval_choices[0][0] == 0:
                self.fields["amount"].label = _("One time donation amount")
            else:
                self.fields["amount"].label = _(
                    "Your {recurring} donation amount"
                ).format(recurring=interval_choices[0][1])

        if all(x[0] > 0 for x in interval_choices):
            # Don't show purpose if all interval options are recurring
            show_purpose = False

        if not show_purpose:
            # No once option -> not choosing purpose
            self.fields["purpose"].widget = forms.HiddenInput()

        self.fields["amount"].widget.presets = self.settings["amount_presets"]
        self.fields["reference"].initial = self.settings["reference"]
        self.fields["keyword"].initial = self.settings["keyword"]
        if self.settings["purpose"]:
            purpose = self.settings["purpose"]
            purpose_split = purpose.split(",")
            if len(purpose_split) == 1:
                purpose_choices = [(purpose, purpose)]
                self.fields["purpose"].initial = purpose
                self.fields["purpose"].choices = purpose_choices
                self.fields["purpose"].widget = forms.HiddenInput()
            else:
                purpose_choices = [(purpose, purpose) for purpose in purpose_split]
                self.fields["purpose"].choices = purpose_choices
        else:
            self.fields["purpose"].widget = forms.HiddenInput()

    def get_interval_choices(self) -> list[tuple[int, str]]:
        if self.settings["interval"] == ONCE:
            interval_choices = [INTERVAL_CHOICES[0]]
        elif not self.settings["interval_choices"]:
            interval_choices = []
            if self.settings["interval"] in (ONCE, ONCE_RECURRING):
                interval_choices.append(INTERVAL_CHOICES[0])
            if self.settings["interval"] in (ONCE_RECURRING, RECURRING):
                interval_choices.extend(INTERVAL_CHOICES[1:])
        else:
            interval_choices = self.settings["interval_choices"]
            if self.settings["interval"] == RECURRING:
                interval_choices = [
                    x for x in interval_choices if x != INTERVAL_CHOICES[0][0]
                ]
            interval_choices = [x for x in INTERVAL_CHOICES if x[0] in interval_choices]
        return interval_choices

    @property
    def prefilled_amount_label(self):
        amount = self.initial.get("amount", self.settings["initial_amount"])
        interval = self.initial.get("interval", self.settings["initial_interval"])
        if interval and interval > 0:
            str_interval = interval_description(interval)
            return _("{amount} EUR {str_interval}.").format(
                amount=amount,
                str_interval=str_interval,
            )
        return _("{amount} EUR.").format(
            amount=amount,
        )

    def clean(self):
        amount = self.cleaned_data.get("amount")
        payment_method = self.cleaned_data.get("payment_method", QUICKPAYMENT_METHOD)
        if amount is not None and payment_method is not None:
            max_amount = PAYMENT_METHOD_MAX_AMOUNT.get(payment_method)
            if max_amount is not None and amount >= max_amount:
                raise forms.ValidationError(
                    _(
                        "Your amount is too large for the chosen payment method. "
                        "Please choose a different method or contact us."
                    )
                )

    def get_payment_metadata(self, data):
        if data["interval"] > 0:
            return {
                "category": _("Donation for %s") % settings.SITE_NAME,
                "plan_name": _(
                    "{amount} EUR donation {str_interval} to {site_name}"
                ).format(
                    amount=data["amount"],
                    str_interval=interval_description(data["interval"]),
                    site_name=settings.SITE_NAME,
                ),
                "description": _("Donation for %s") % settings.SITE_NAME,
                "kind": "fds_donation.Donation",
            }
        else:
            return {
                "category": _("Donation for %s") % settings.SITE_NAME,
                "description": "{} ({})".format(
                    data.get("purpose", DEFAULT_PURPOSE) or DEFAULT_PURPOSE,
                    settings.SITE_NAME,
                ),
                "kind": "fds_donation.Donation",
            }

    def create_related_object(self, order, data):
        donor = data.get("donor")
        if donor is None:
            donor = get_or_create_donor(
                self.cleaned_data, user=self.user, subscription=order.subscription
            )
        if order.subscription:
            donor.subscriptions.add(order.subscription)

        keyword = data.get("keyword", "")
        if keyword.startswith(settings.SITE_URL):
            keyword = keyword.replace(settings.SITE_URL, "", 1)

        query_params = dict(
            parse_qsl(data.get("query_params", ""), keep_blank_values=True)
        )

        method = data.get("payment_method", QUICKPAYMENT_METHOD)
        recurrence = None
        if order.subscription:
            subscription = order.subscription
            recurrence = Recurrence.objects.create(
                subscription=subscription,
                donor=donor,
                active=False,
                start_date=subscription.created,
                interval=subscription.plan.interval,
                amount=subscription.plan.amount,
                method=method,
                project=DEFAULT_DONATION_PROJECT,
                cancel_date=None,
            )

        donation = Donation.objects.create(
            donor=donor,
            amount=order.total_gross,
            reference=data.get("reference", "")[:1024],
            keyword=keyword[:1024],
            purpose=data.get("purpose", DEFAULT_PURPOSE) or order.description,
            form_url=data.get("form_url", "")[:1024],
            order=order,
            recurring=order.is_recurring,
            first_recurring=order.is_recurring,
            recurrence=recurrence,
            method=method,
            extra_action_url=self.settings.get("next_url", ""),
            extra_action_label=self.settings.get("next_label", ""),
            data={
                "query_params": query_params,
                "form_settings": self.settings,
                "is_quick_payment": data.get("is_quick_payment", False),
            },
        )
        return donation

    def augment_donation_data(self, data):
        data["is_donation"] = True
        return data

    def save(self, extra_data=None):
        data = self.cleaned_data.copy()
        if extra_data is not None:
            data.update(extra_data)
        data = self.augment_donation_data(data)
        order = self.create_order(data)
        related_obj = self.create_related_object(order, data)

        return order, related_obj


class RemoteDonationForm(forms.Form):
    initial_amount = forms.DecimalField(
        localize=True,
        required=True,
        initial=None,
        min_value=MIN_AMOUNT,
        max_digits=19,
        decimal_places=2,
        label=_("Donation amount:"),
        widget=AmountInput(
            attrs={
                "title": _("Amount in Euro, comma as decimal separator"),
                "class": "text-end",
            },
            presets=[],
        ),
    )
    initial_interval = forms.TypedChoiceField(
        choices=[],
        coerce=int,
        empty_value=None,
        required=True,
        label=_("Frequency"),
        widget=InlineBootstrapRadioSelect,
    )
    pk_campaign = forms.CharField(required=False, widget=forms.HiddenInput())
    pk_keyword = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.settings = kwargs.pop("form_settings", DonationFormFactory.default)
        super().__init__(*args, **kwargs)

        interval_choices = self.get_interval_choices()
        self.fields["initial_interval"].choices = interval_choices
        self.fields["initial_interval"].initial = (
            self.settings.get("initial_interval", None) or interval_choices[0][0]
        )
        self.fields["initial_amount"].widget.presets = self.settings["amount_presets"]
        self.fields["initial_amount"].initial = self.settings["initial_amount"]
        self.fields["pk_campaign"].initial = self.settings["reference"]
        self.fields["pk_keyword"].initial = self.settings["keyword"]

        if len(interval_choices) == 1:
            self.fields["initial_interval"].initial = interval_choices[0][0]
            self.fields["initial_interval"].widget = forms.HiddenInput()
            if interval_choices[0][0] == 0:
                self.fields["initial_amount"].label = _("One time donation amount")
            else:
                self.fields["initial_amount"].label = _(
                    "Your {recurring} donation amount"
                ).format(recurring=interval_choices[0][1])

    get_interval_choices = BasicDonationForm.get_interval_choices


class SimpleDonationForm(BasicDonationForm):
    payment_method = forms.ChoiceField(
        label=_("Payment method"),
        choices=None,
        widget=BootstrapRadioSelect,
        initial=PAYMENT_METHODS[0][0],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Payment method choices
        self.fields["payment_method"].choices = [
            (x, CHECKOUT_PAYMENT_CHOICES_DICT.get(x, x))
            for x in self.settings["payment_methods"]
        ]
        if len(self.fields["payment_method"].choices) == 1:
            self.fields["payment_method"].initial = self.fields[
                "payment_method"
            ].choices[0][0]
            self.fields["payment_method"].widget = forms.HiddenInput()
            self.payment_method_label = _("You are paying with {method}.").format(
                method=self.fields["payment_method"].choices[0][1]
            )


COUNTRY_CHOICES = (
    ("", "---"),
    ("DE", _("Germany")),
    # Germany, its neighbours and German speaking countries
    ("AT", _("Austria")),
    ("CH", _("Switzerland")),
    ("BE", _("Belgium")),
    ("NL", _("Netherlands")),
    ("LU", _("Luxembourg")),
    ("FR", _("France")),
    ("LI", _("Liechtenstein")),
    ("DK", _("Denmark")),
    ("PL", _("Poland")),
    ("CZ", _("Czech Republic")),
    # And some more EU countries
    ("IT", _("Italy")),
    ("ES", _("Spain")),
    ("PT", _("Portugal")),
    ("SE", _("Sweden")),
    ("FI", _("Finland")),
)


def get_basic_info_fields(
    prefix=None, name_required=True, country_choices=COUNTRY_CHOICES
):
    fields = {
        "first_name": forms.CharField(
            max_length=255,
            label=_("First name"),
            required=name_required,
            validators=[validate_not_too_many_uppercase],
            widget=forms.TextInput(
                attrs={"placeholder": _("First name"), "class": "form-control"}
            ),
        ),
        "last_name": forms.CharField(
            max_length=255,
            label=_("Last name"),
            required=name_required,
            widget=forms.TextInput(
                attrs={"placeholder": _("Last name"), "class": "form-control"}
            ),
        ),
        "address": forms.CharField(
            max_length=255,
            label=_("Street, house number"),
            required=False,
            widget=forms.TextInput(
                attrs={
                    "placeholder": _("Street, house number"),
                    "class": "form-control",
                }
            ),
        ),
        "postcode": forms.CharField(
            max_length=20,
            label=_("Postcode"),
            required=False,
            widget=forms.TextInput(
                attrs={"placeholder": _("Postcode"), "class": "form-control"}
            ),
        ),
        "city": forms.CharField(
            max_length=255,
            label=_("City"),
            required=False,
            widget=forms.TextInput(
                attrs={"placeholder": _("City"), "class": "form-control"}
            ),
        ),
        "country": forms.ChoiceField(
            label=_("Country"),
            required=False,
            choices=country_choices,
            widget=BootstrapSelect,
        ),
    }
    if prefix:
        fields = {"{}_{}".format(prefix, k): v for k, v in fields.items()}

    return fields


def get_basic_info_form(**kwargs):
    fields = get_basic_info_fields(**kwargs)
    return type("BasicInfoForm", (forms.Form,), fields)


class BasicDonorForm(get_basic_info_form(), forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": _("e.g. name@example.org")}
        ),
    )


class DonorForm(BasicDonorForm):
    salutation = forms.ChoiceField(
        label=_("Salutation"),
        required=False,
        choices=SALUTATION_CHOICES,
        widget=BootstrapSelect,
    )
    company_name = forms.CharField(
        label=_("Company"),
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Company name")}
        ),
    )

    receipt = forms.TypedChoiceField(
        widget=InlineBootstrapRadioSelect(
            attrs={
                "data-toggle": "radiocollapse",
                "data-target": "address-fields",
            }
        ),
        choices=(
            (0, _("No, thank you.")),
            (1, _("Yes, once a year via email.")),
        ),
        coerce=lambda x: bool(int(x)),
        required=True,
        initial=0,
        label=_("Do you want a donation receipt?"),
        error_messages={"required": _("You have to decide.")},
    )

    @override
    def clean(self):
        cleaned_data = cast(dict, super().clean())
        if cleaned_data.get("receipt"):
            fields = get_basic_info_fields().keys()
            missing_fields = [field for field in fields if not cleaned_data.get(field)]
            for field in missing_fields:
                self.add_error(
                    field,
                    _(
                        "In order to receive donation receipts, please fill out this field."
                    ),
                )

        return cleaned_data


class DonationGiftLogic:
    @staticmethod
    def init(form: BasicDonationForm):
        if not form.settings["gift_options"]:
            return
        gift_options = DonationGift.objects.available().filter(
            id__in=form.settings["gift_options"]
        )
        if gift_options:
            form.fields["chosen_gift"] = forms.ModelChoiceField(
                widget=BootstrapSelect,
                queryset=gift_options,
                label=_("Donation gift"),
                error_messages={
                    "invalid_choice": _(
                        "The chosen donation gift is no longer available, sorry!"
                    )
                },
            )
            form.fields.update(
                get_basic_info_fields(prefix="shipping", name_required=False)
            )
            if len(gift_options) == 1:
                form.fields["chosen_gift"].widget = forms.HiddenInput()
                form.fields["chosen_gift"].initial = gift_options[0].id
            elif form.settings["default_gift"]:
                form.fields["chosen_gift"].initial = form.settings["default_gift"]
        else:
            form.gift_error_message = _(
                "Unfortunately, all available donation gifts have been reserved."
            )

    @staticmethod
    def clean(form: BasicDonationForm):
        if not form.settings["gift_options"]:
            return

        chosen_gift = form.cleaned_data.get("chosen_gift")
        if chosen_gift is None:
            return
        if not chosen_gift.has_remaining_available_to_order():
            form.add_error(
                "chosen_gift",
                _("The chosen donation gift is no longer available, sorry!"),
            )

        # Check if any address is given
        address_fields = ("address", "postcode", "city", "country")
        for address_field in address_fields:
            shipping_field = "shipping_{}".format(address_field)
            if not form.cleaned_data.get(address_field) and not form.cleaned_data.get(
                shipping_field
            ):
                form.add_error(
                    shipping_field, _("Please complete your shipping address.")
                )


class QuickDonationForm(BasicDonationForm, BasicDonorForm):
    payment_method = QUICKPAYMENT_METHOD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        DonationGiftLogic.init(self)

    def clean(self):
        super().clean()

        DonationGiftLogic.clean(self)

        return self.cleaned_data

    def augment_donation_data(self, data):
        data = super().augment_donation_data(data)
        data["payment_method"] = QUICKPAYMENT_METHOD
        data["is_quick_payment"] = True
        return data


class DonationForm(SpamProtectionMixin, SimpleDonationForm, DonorForm):
    form_settings = forms.CharField(widget=forms.HiddenInput)
    contact = forms.TypedChoiceField(
        widget=BootstrapRadioSelect,
        choices=(
            (1, _("Yes, please!")),
            (0, _("No, thank you.")),
        ),
        coerce=lambda x: bool(int(x)),
        required=True,
        label=_("News"),
        error_messages={"required": _("You have to decide.")},
    )
    account = forms.TypedChoiceField(
        widget=BootstrapRadioSelect,
        choices=(),
        coerce=lambda x: bool(int(x)),
        required=True,
        label=_(
            "With your donation you can also create a "
            "FragDenStaat account where you can manage your "
            "details, donations and requests."
        ),
        error_messages={"required": _("You have to decide.")},
    )

    SPAM_PROTECTION = {
        "captcha": "ip",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.user is not None:
            self.fields["email"].initial = self.user.email
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial = self.user.last_name
            parsed = parse_address(self.user.address)
            self.fields["address"].initial = parsed.get("address", "")
            self.fields["postcode"].initial = parsed.get("postcode", "")
            self.fields["city"].initial = parsed.get("city", "")
            self.fields["country"].initial = "DE"
            self.fields.pop("account")
        else:
            self.fields["account"].choices = (
                (
                    1,
                    format_html(
                        'Ja, super praktisch. Ich stimme den <a href="{url_terms}" target="_blank">'
                        "Nutzungsbedingungen</a> zu.",
                        url_terms=get_content_url("terms"),
                    ),
                ),
                (0, _("No, thank you.")),
            )
        if self.settings["hide_account"] and "account" in self.fields:
            self.fields.pop("account")

        if self.settings["hide_contact"] and "contact" in self.fields:
            self.fields.pop("contact")

        DonationGiftLogic.init(self)

    def clean(self):
        super().clean()

        # Check if gift options are valid
        DonationGiftLogic.clean(self)

        return self.cleaned_data

    def save(self, **kwargs):
        order, donation = super().save(**kwargs)

        if self.cleaned_data.get("chosen_gift"):
            donor = donation.donor
            DonationGiftOrder.objects.create(
                donation=donation,
                donation_gift=self.cleaned_data["chosen_gift"],
                first_name=self.cleaned_data["shipping_first_name"] or donor.first_name,
                last_name=self.cleaned_data["shipping_last_name"] or donor.last_name,
                address=self.cleaned_data["shipping_address"] or donor.address,
                postcode=self.cleaned_data["shipping_postcode"] or donor.postcode,
                city=self.cleaned_data["shipping_city"] or donor.city,
                country=self.cleaned_data["shipping_country"] or donor.country,
                email=donor.email,
            )

        return order, donation


class DonationGiftForm(SpamProtectionMixin, forms.Form):
    name = forms.CharField(
        max_length=255,
        label=_("Your name"),
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        max_length=255,
        label=_("Your email address"),
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    address = forms.CharField(
        label=_("Shipping address"),
        widget=forms.Textarea(attrs={"class": "form-control", "rows": "3"}),
    )
    gift = forms.ModelChoiceField(
        label=_("Please choose your donation gift"), queryset=None
    )

    SPAM_PROTECTION = {
        "captcha": "always",
    }

    def __init__(self, *args, **kwargs):
        self.category = kwargs.pop("category")
        super().__init__(*args, **kwargs)
        gifts = DonationGift.objects.filter(category_slug=self.category)
        self.fields["gift"].queryset = gifts
        if len(gifts) == 1:
            self.fields["gift"].initial = gifts[0].id
            self.fields["gift"].widget = forms.HiddenInput()

    def save(self, request=None):
        text = [
            "Name",
            self.cleaned_data["name"],
            "E-Mail",
            self.cleaned_data["email"],
            "Auswahl",
            self.cleaned_data["gift"],
            "Adresse",
            self.cleaned_data["address"],
        ]
        if request and request.user:
            text.extend(["User", request.user.id])

        mail_managers(
            "Neue Bestellung von %s" % self.category,
            str("\n".join(str(t) for t in text)),
        )


def get_merge_donor_form(admin_site):
    class MergeDonorForm(forms.ModelForm):
        class Meta:
            model = Donor
            fields = MERGE_DONOR_FIELDS
            widgets = {
                "user": ForeignKeyRawIdWidget(
                    Donor._meta.get_field("user").remote_field, admin_site
                ),
                "subscriber": ForeignKeyRawIdWidget(
                    Donor._meta.get_field("subscriber").remote_field, admin_site
                ),
            }

    return MergeDonorForm


class DonorDetailsForm(DonorForm, forms.ModelForm):
    class Meta:
        model = Donor
        fields = [
            "salutation",
            "first_name",
            "last_name",
            "company_name",
            "address",
            "city",
            "postcode",
            "country",
            # 'email', # TODO: implement email confirmation flow
            "receipt",
        ]

    email = None

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance:
            initial = kwargs.pop("initial", {})
            if instance.receipt is not None:
                initial.update(
                    {
                        "receipt": int(instance.receipt),
                    }
                )
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)


class SubscriptionCancelFeedbackForm(forms.Form):
    reason = forms.ChoiceField(
        label=_("Reason for cancellation"),
        required=False,
        choices=CancelReason.choices,
        widget=BootstrapSelect,
    )
    feedback = forms.CharField(
        label=_("Feedback"),
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": _("How are you feeling about canceling?"),
            }
        ),
    )

    def save(self, subscription):
        try:
            recurrence = Recurrence.objects.get(subscription=subscription)
        except Recurrence.DoesNotExist:
            return
        recurrence.cancel_reason = self.cleaned_data.get("reason")
        recurrence.cancel_feedback = self.cleaned_data.get("feedback")
        recurrence.save(update_fields=["cancel_reason", "cancel_feedback"])
