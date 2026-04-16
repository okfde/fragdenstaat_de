from django import forms
from django.conf import settings


class AmountInput(forms.TextInput):
    template_name = "fds_donation/forms/widgets/amount_input.html"

    def __init__(self, presets=None, amount_label=None, **kwargs):
        super().__init__(**kwargs)
        self.presets = presets or []
        self.amount_label = amount_label or settings.DEFAULT_CURRENCY_LABEL

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        ctx["widget"].setdefault("attrs", {})
        ctx["widget"]["attrs"]["class"] = (
            ctx["widget"]["attrs"].get("class", "") + " form-control col-3"
        )
        ctx["widget"]["attrs"].setdefault("inputmode", "decimal")
        ctx["widget"]["attrs"]["pattern"] = "[\\d\\.,]*"
        ctx["widget"]["attrs"]["autocomplete"] = "off"
        ctx["currency"] = settings.FROIDE_CONFIG["currency"]
        ctx["amount_label"] = self.amount_label
        ctx["presets"] = self.presets
        return ctx
