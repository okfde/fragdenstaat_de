import base64
import json
import logging

from django import forms
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme

from .models import (
    INTERVAL_CHOICES,
    INTERVAL_SETTINGS_CHOICES,
    MAX_AMOUNT,
    MIN_AMOUNT,
    ONCE_RECURRING,
    PAYMENT_METHODS,
    QUICKPAYMENT_CHOICES,
)

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
    quick_payment = forms.ChoiceField(
        choices=QUICKPAYMENT_CHOICES,
        required=False,
        initial="",
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
        "quick_payment": "",
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
        "prefilled_amount",
    }

    def __init__(self, **kwargs):
        self.settings = {}
        for key in self.default:
            self.settings[key] = kwargs.get(key, self.default[key])

    @classmethod
    def from_request(cls, request):
        data = {}
        if request.GET.get("initial_amount"):
            data["prefilled_amount"] = True

        for key in cls.request_configurable:
            value = request.GET.get(key)
            if value:
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
        from .forms import DonationForm

        form_class = kwargs.pop("form_class", DonationForm)

        kwargs = self.get_form_kwargs(**kwargs)
        return form_class(**kwargs)

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
