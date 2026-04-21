from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from fragdenstaat_de.fds_donation.utils import format_amount_with_currency


class AmountInput(forms.TextInput):
    template_name = "fds_donation/forms/widgets/amount_input.html"

    def __init__(self, presets=None, amount_label=None, min_value=0, **kwargs):
        super().__init__(**kwargs)
        self.presets = presets or []
        self.min_value = min_value
        self.amount_label = (
            settings.DEFAULT_CURRENCY_LABEL if amount_label is None else ""
        )

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["widget"].setdefault("attrs", {})
        ctx["widget"]["attrs"]["class"] = (
            ctx["widget"]["attrs"].get("class", "") + " amount-input form-control"
        )
        ctx["widget"]["attrs"].setdefault("inputmode", "decimal")
        ctx["widget"]["attrs"]["pattern"] = r"^(\d+)([.,]\d{1,2})?$"
        ctx["widget"]["attrs"]["autocomplete"] = "off"
        ctx["widget"]["attrs"]["size"] = "6"
        ctx["widget"]["attrs"]["title"] = _(
            "Enter a number with up to two decimal places."
        )
        ctx["widget"]["attrs"].setdefault("data-min", self.min_value)
        ctx["widget"]["attrs"]["data-errormin"] = _(
            "The amount needs to be at least {}."
        ).format(format_amount_with_currency(self.min_value))
        ctx["currency"] = settings.FROIDE_CONFIG["currency"]
        ctx["amount_label"] = self.amount_label
        ctx["presets"] = self.presets
        return ctx
