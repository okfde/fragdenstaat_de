import base64
import json
import logging
from urllib.parse import parse_qsl

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.mail import mail_managers
from django.core.validators import MinValueValidator
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
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

from .models import (
    CHECKOUT_PAYMENT_CHOICES_DICT,
    INTERVAL_CHOICES,
    INTERVAL_SETTINGS_CHOICES,
    MAX_AMOUNT,
    MIN_AMOUNT,
    ONCE,
    ONCE_RECURRING,
    PAYMENT_METHOD_MAX_AMOUNT,
    PAYMENT_METHODS,
    RECURRING,
    SALUTATION_CHOICES,
    Donation,
    DonationGift,
    DonationGiftOrder,
    Donor,
)
from .services import get_or_create_donor
from .utils import MERGE_DONOR_FIELDS
from .validators import validate_not_too_many_uppercase
from .widgets import AmountInput

logger = logging.getLogger(__name__)


class DonationSettingsForm(forms.Form):
    title = forms.CharField(required=False)
    interval = forms.ChoiceField(
        choices=INTERVAL_SETTINGS_CHOICES,
        required=False,
        initial=ONCE_RECURRING,
    )
    interval_choices = forms.RegexField(
        regex=r"(\d+(?:,\d+)*|\-)",
        required=False,
    )
    amount_presets = forms.RegexField(
        regex=r"(\d+(?:,\d+)*|\-)",
        required=False,
    )
    gift_options = forms.RegexField(
        regex=r"(\d+(?:,\d+)*|\-)",
        required=False,
    )
    default_gift = forms.IntegerField(required=False)
    reference = forms.CharField(required=False)
    keyword = forms.CharField(required=False)
    purpose = forms.CharField(required=False)
    initial_amount = forms.IntegerField(
        required=False, min_value=MIN_AMOUNT, max_value=MAX_AMOUNT
    )
    min_amount = forms.IntegerField(
        min_value=MIN_AMOUNT, max_value=MAX_AMOUNT, initial=0, required=False
    )
    initial_interval = forms.IntegerField(
        required=False,
    )
    prefilled_amount = forms.BooleanField(required=False)
    initial_receipt = forms.BooleanField(required=False)
    hide_contact = forms.BooleanField(required=False, initial=False)
    hide_account = forms.BooleanField(required=False, initial=False)
    collapsed = forms.BooleanField(required=False)
    payment_methods = forms.CharField(
        required=False,
    )

    next_url = forms.CharField(required=False)
    next_label = forms.CharField(required=False)

    def clean_interval_choices(self):
        presets = self.cleaned_data["interval_choices"]
        if not presets:
            return DonationFormFactory.default["interval_choices"]
        try:
            values = [int(x.strip()) for x in presets.split(",") if x.strip()]
            values = [
                x
                for x in values
                if x in DonationFormFactory.default["interval_choices"]
            ]
            return values
        except ValueError:
            return []

    def clean_amount_presets(self):
        presets = self.cleaned_data["amount_presets"]
        if presets == "-":
            return []
        if not presets:
            return DonationFormFactory.default["amount_presets"]
        try:
            return [int(x.strip()) for x in presets.split(",") if x.strip()]
        except ValueError:
            return []

    def clean_payment_methods(self):
        presets = self.cleaned_data["payment_methods"]
        if not presets:
            return DonationFormFactory.default["payment_methods"]

        values = [x.strip() for x in presets.split(",") if x.strip()]
        values = [
            x for x in values if x in DonationFormFactory.default["payment_methods"]
        ]
        if not values:
            return DonationFormFactory.default["payment_methods"]
        return values

    def clean_gift_options(self):
        gift_options = self.cleaned_data["gift_options"]
        if not gift_options or gift_options == "-":
            return []
        try:
            return [int(x.strip()) for x in gift_options.split(",") if x.strip()]
        except ValueError:
            return []

    def clean_initial_receipt(self):
        receipt = self.cleaned_data["initial_receipt"]
        return int(receipt)

    def clean_next_url(self):
        next_url = self.cleaned_data["next_url"]
        if url_has_allowed_host_and_scheme(
            next_url, allowed_hosts=settings.ALLOWED_REDIRECT_HOSTS
        ):
            return next_url
        return ""

    def make_donation_form(self, **kwargs):
        d = {}
        if self.is_valid():
            d = self.cleaned_data
        else:
            logger.warning(("Donation settings form not valid: %s", self.errors))
        return DonationFormFactory(**d).make_form(**kwargs)


class DonationFormFactory:
    default = {
        "title": "",
        "interval": ONCE_RECURRING,
        "interval_choices": [x[0] for x in INTERVAL_CHOICES],
        "reference": "",
        "keyword": "",
        "purpose": "",
        "amount_presets": [5, 20, 50],
        "initial_amount": None,
        "min_amount": MIN_AMOUNT,
        "gift_options": [],
        "prefilled_amount": False,
        "default_gift": None,
        "initial_interval": 0,
        "initial_receipt": "0",
        "collapsed": False,
        "next_url": "",
        "next_label": "",
        "payment_methods": [x[0] for x in PAYMENT_METHODS],
        "hide_contact": False,
        "hide_account": False,
    }
    initials = {
        "initial_amount": "amount",
        "initial_interval": "interval",
        "initial_receipt": "receipt",
    }
    request_configurable = {
        "amount_presets",
        "initial_amount",
        "initial_interval",
        "interval",
        "min_amount",
        "purpose",
    }

    def __init__(self, **kwargs):
        self.settings = {}
        for key in self.default:
            self.settings[key] = kwargs.get(key, self.default[key])

    @classmethod
    def from_request(cls, request):
        data = {}
        for key in cls.request_configurable:
            value = request.GET.get(key)
            if value is not None:
                data[key] = value
        return data

    def get_form_kwargs(self, **kwargs):
        if "data" in kwargs:
            form_settings = kwargs["data"].get("form_settings")
            raw_data = self.deserialize(form_settings)
            settings_form = DonationSettingsForm(data=raw_data)
            if settings_form.is_valid():
                self.settings.update(settings_form.cleaned_data)
            else:
                logger.warning(
                    "Donation settings form via data not valid: %s",
                    settings_form.errors,
                )

        kwargs.setdefault("initial", {})
        kwargs["initial"]["form_settings"] = self.serialize()
        for k, v in self.initials.items():
            if self.settings[k] is not None:
                kwargs["initial"][v] = self.settings[k]

        kwargs["form_settings"] = self.settings
        return kwargs

    def make_form(self, **kwargs):
        kwargs = self.get_form_kwargs(**kwargs)
        return DonationForm(**kwargs)

    def serialize(self):
        return base64.b64encode(json.dumps(self.settings).encode("utf-8")).decode(
            "utf-8"
        )

    def deserialize(self, encoded):
        if encoded is None:
            return self.default
        try:
            decoded_bytes = base64.b64decode(encoded)
        except ValueError:
            return self.default
        try:
            unicode_str = decoded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return self.default
        try:
            raw_data = json.loads(unicode_str)
        except ValueError:
            return self.default
        return {
            k: ",".join(str(x) for x in v) if isinstance(v, list) else v
            for k, v in raw_data.items()
        }


class SimpleDonationForm(StartPaymentMixin, forms.Form):
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
            (_("General donation"), _("General donation")),
        ],
        widget=BootstrapSelect(
            attrs={"data-toggle": "nonrecurring"},
        ),
    )
    reference = forms.CharField(required=False, widget=forms.HiddenInput())
    keyword = forms.CharField(required=False, widget=forms.HiddenInput())
    form_url = forms.CharField(required=False, widget=forms.HiddenInput())
    query_params = forms.CharField(required=False, widget=forms.HiddenInput())
    payment_method = forms.ChoiceField(
        label=_("Payment method"),
        choices=None,
        widget=BootstrapRadioSelect,
        initial=PAYMENT_METHODS[0][0],
    )

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
        if interval > 0:
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
        payment_method = self.cleaned_data.get("payment_method")
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
                "description": "{} ({})".format(data["purpose"], settings.SITE_NAME),
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

        donation = Donation.objects.create(
            donor=donor,
            amount=order.total_gross,
            reference=data.get("reference", ""),
            keyword=keyword,
            purpose=data.get("purpose", "") or order.description,
            form_url=data.get("form_url", ""),
            order=order,
            recurring=order.is_recurring,
            first_recurring=order.is_recurring,
            method=data.get("payment_method", ""),
            extra_action_url=self.settings.get("next_url", ""),
            extra_action_label=self.settings.get("next_label", ""),
            data={
                "query_params": query_params,
                "form_settings": self.settings,
            },
        )
        return donation

    def save(self, extra_data=None):
        data = self.cleaned_data.copy()
        if extra_data is not None:
            data.update(extra_data)
        data["is_donation"] = True
        order = self.create_order(data)
        related_obj = self.create_related_object(order, data)

        return order, related_obj


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


class DonorForm(get_basic_info_form(), forms.Form):
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

    email = forms.EmailField(
        label=_("Email"),
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": _("e.g. name@example.org")}
        ),
    )


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

        if self.settings["gift_options"]:
            gift_options = DonationGift.objects.available().filter(
                id__in=self.settings["gift_options"]
            )
            if gift_options:
                self.fields["chosen_gift"] = forms.ModelChoiceField(
                    widget=BootstrapSelect,
                    queryset=gift_options,
                    label=_("Donation gift"),
                    error_messages={
                        "invalid_choice": _(
                            "The chosen donation gift is no longer available, sorry!"
                        )
                    },
                )
                self.fields.update(
                    get_basic_info_fields(prefix="shipping", name_required=False)
                )
                if len(gift_options) == 1:
                    self.fields["chosen_gift"].widget = forms.HiddenInput()
                    self.fields["chosen_gift"].initial = gift_options[0].id
                elif self.settings["default_gift"]:
                    self.fields["chosen_gift"].initial = self.settings["default_gift"]
            else:
                self.gift_error_message = _(
                    "Unfortunately, all available donation gifts have been reserved."
                )

    def clean(self):
        if not self.settings["gift_options"]:
            return

        chosen_gift = self.cleaned_data.get("chosen_gift")
        if chosen_gift is None:
            return
        if not chosen_gift.has_remaining_available_to_order():
            self.add_error(
                "chosen_gift",
                _("The chosen donation gift is no longer available, sorry!"),
            )

        # Check if any address is given
        address_fields = ("address", "postcode", "city", "country")
        for address_field in address_fields:
            shipping_field = "shipping_{}".format(address_field)
            if not self.cleaned_data.get(address_field) and not self.cleaned_data.get(
                shipping_field
            ):
                self.add_error(
                    shipping_field, _("Please complete your shipping address.")
                )

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


class DonorDetailsForm(forms.ModelForm, DonorForm):
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
            initial.update(
                {
                    "receipt": int(instance.receipt),
                }
            )
            kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
