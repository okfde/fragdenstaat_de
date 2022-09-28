import base64
import decimal
import json

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.mail import mail_managers
from django.core.validators import MinValueValidator
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from froide.account.utils import parse_address
from froide.campaign.models import Campaign
from froide.helper.content_urls import get_content_url
from froide.helper.spam import SpamProtectionMixin
from froide.helper.widgets import (
    BootstrapRadioSelect,
    BootstrapSelect,
    InlineBootstrapRadioSelect,
)

from froide_payment.forms import StartPaymentMixin
from froide_payment.models import CHECKOUT_PAYMENT_CHOICES_DICT
from froide_payment.utils import interval_description

from .models import (
    INTERVAL_SETTINGS_CHOICES,
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

PAYMENT_METHOD_LIST = (
    "sepa",
    "paypal",
    "banktransfer",
    "creditcard",
    # "sofort",
)
MIN_AMOUNT = 5
PAYMENT_METHOD_MAX_AMOUNT = {"sepa": decimal.Decimal(5000)}

PAYMENT_METHODS = [
    (method, CHECKOUT_PAYMENT_CHOICES_DICT[method]) for method in PAYMENT_METHOD_LIST
]


class DonationSettingsForm(forms.Form):
    title = forms.CharField(required=False)
    interval = forms.ChoiceField(
        choices=INTERVAL_SETTINGS_CHOICES,
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
        required=False,
    )
    min_amount = forms.IntegerField(
        required=False,
    )
    initial_interval = forms.IntegerField(
        required=False,
    )
    initial_receipt = forms.BooleanField(required=False)
    collapsed = forms.BooleanField(required=False)

    def clean_amount_presets(self):
        presets = self.cleaned_data["amount_presets"]
        if presets == "-":
            return []
        if not presets:
            return [5, 20, 50]
        if "[" in presets:
            presets = presets.replace("[", "").replace("]", "")
        try:
            return [int(x.strip()) for x in presets.split(",") if x.strip()]
        except ValueError:
            return []

    def clean_gift_options(self):
        gift_options = self.cleaned_data["gift_options"]
        if not gift_options or gift_options == "-":
            return []
        if "[" in gift_options:
            gift_options = gift_options.replace("[", "").replace("]", "")
        try:
            return [int(x.strip()) for x in gift_options.split(",") if x.strip()]
        except ValueError:
            return []

    def clean_initial_receipt(self):
        receipt = self.cleaned_data["initial_receipt"]
        return int(receipt)

    def make_donation_form(self, **kwargs):
        d = {}
        if self.is_valid():
            d = self.cleaned_data
        return DonationFormFactory(**d).make_form(**kwargs)


class DonationFormFactory:
    default = {
        "title": "",
        "interval": "once_recurring",
        "reference": "",
        "keyword": "",
        "purpose": "",
        "amount_presets": [5, 20, 50],
        "initial_amount": None,
        "min_amount": MIN_AMOUNT,
        "gift_options": [],
        "default_gift": None,
        "initial_interval": 0,
        "initial_receipt": "0",
        "collapsed": False,
    }
    initials = {
        "initial_amount": "amount",
        "initial_interval": "interval",
        "initial_receipt": "receipt",
    }

    def __init__(self, **kwargs):
        self.settings = {}
        for key in self.default:
            self.settings[key] = kwargs.get(key, self.default[key])

    def get_form_kwargs(self, **kwargs):
        if "data" in kwargs:
            form_settings = kwargs["data"].get("form_settings")
            raw_data = self.deserialize(form_settings)
            settings_form = DonationSettingsForm(data=raw_data)
            if settings_form.is_valid():
                self.settings.update(settings_form.cleaned_data)

        kwargs.setdefault("initial", {})
        kwargs["initial"]["form_settings"] = self.serialize()
        for k, v in self.initials.items():
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
        return raw_data


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
    payment_method = forms.ChoiceField(
        label=_("Payment method"),
        choices=PAYMENT_METHODS,
        widget=BootstrapRadioSelect,
        initial=PAYMENT_METHODS[0][0],
    )

    def __init__(self, *args, **kwargs):
        self.action = kwargs.pop("action", None)

        user = kwargs.pop("user", None)
        if not user.is_authenticated:
            user = None
        self.user = user
        self.settings = kwargs.pop("form_settings", DonationFormFactory.default)

        super().__init__(*args, **kwargs)

        if self.settings["min_amount"] and self.settings["min_amount"] >= MIN_AMOUNT:
            self.fields["amount"].min_value = self.settings["min_amount"]
            self.fields["amount"].validators.append(
                MinValueValidator(self.settings["min_amount"])
            )

        interval_choices = []
        has_purpose = True
        if "once" in self.settings["interval"]:
            interval_choices.append(
                ("0", _("once")),
            )
        else:
            # No once option -> not choosing purpose
            has_purpose = False
            self.fields["purpose"].widget = forms.HiddenInput()
        if "recurring" in self.settings["interval"]:
            interval_choices.extend(
                [
                    ("1", _("monthly")),
                    ("3", _("quarterly")),
                    ("12", _("yearly")),
                ]
            )

        self.fields["interval"].choices = interval_choices
        if self.settings["interval"] == "once":
            self.fields["interval"].initial = "0"
            self.fields["interval"].widget = forms.HiddenInput()
            self.fields["amount"].label = _("One time donation amount")

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
        elif has_purpose:
            choices = [(x.name, x.name) for x in Campaign.objects.get_filter_list()]
            self.fields["purpose"].widget.choices.extend(choices)
            self.fields["purpose"].choices.extend(choices)

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

        donation = Donation.objects.create(
            donor=donor,
            amount=order.total_gross,
            reference=data.get("reference", ""),
            keyword=keyword,
            purpose=data.get("purpose", "") or order.description,
            order=order,
            recurring=order.is_recurring,
            first_recurring=order.is_recurring,
            method=data.get("payment_method", ""),
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
    fields = dict(
        first_name=forms.CharField(
            max_length=255,
            label=_("First name"),
            required=name_required,
            validators=[validate_not_too_many_uppercase],
            widget=forms.TextInput(
                attrs={"placeholder": _("First name"), "class": "form-control"}
            ),
        ),
        last_name=forms.CharField(
            max_length=255,
            label=_("Last name"),
            required=name_required,
            widget=forms.TextInput(
                attrs={"placeholder": _("Last name"), "class": "form-control"}
            ),
        ),
        address=forms.CharField(
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
        postcode=forms.CharField(
            max_length=20,
            label=_("Postcode"),
            required=False,
            widget=forms.TextInput(
                attrs={"placeholder": _("Postcode"), "class": "form-control"}
            ),
        ),
        city=forms.CharField(
            max_length=255,
            label=_("City"),
            required=False,
            widget=forms.TextInput(
                attrs={"placeholder": _("City"), "class": "form-control"}
            ),
        ),
        country=forms.ChoiceField(
            label=_("Country"),
            required=False,
            choices=country_choices,
            widget=BootstrapSelect,
        ),
    )
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
        if self.settings["gift_options"]:
            gift_options = DonationGift.objects.filter(
                id__in=self.settings["gift_options"]
            )
            if gift_options:
                self.fields["chosen_gift"] = forms.ModelChoiceField(
                    widget=BootstrapSelect,
                    queryset=gift_options,
                    label=_("Donation gift"),
                )
                self.fields.update(
                    get_basic_info_fields(prefix="shipping", name_required=False)
                )
            if len(gift_options) == 1:
                self.fields["chosen_gift"].widget = forms.HiddenInput()
                self.fields["chosen_gift"].initial = gift_options[0].id
            elif self.settings["default_gift"]:
                self.fields["chosen_gift"].initial = self.settings["default_gift"]

    def clean(self):
        if not self.settings["gift_options"]:
            return

        # Check if any address is given
        address_fields = ("address", "postcode", "city", "country")
        for address_field in address_fields:
            shipping_field = "shipping_{}".format(address_field)
            if (
                not self.cleaned_data[address_field]
                and not self.cleaned_data[shipping_field]
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
