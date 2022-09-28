from django import forms

from .models import ABTestEvent


class ABTestEventForm(forms.ModelForm):
    class Meta:
        model = ABTestEvent
        fields = ["ab_test", "variant"]
        widgets = {"ab_test": forms.HiddenInput(), "variant": forms.HiddenInput()}
