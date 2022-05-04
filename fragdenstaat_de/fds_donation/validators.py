import re

from django import forms

UPPERCASE_LETTERS = re.compile(r"[A-Z]")


def validate_not_too_many_uppercase(name):
    if " " in name:
        return
    if len(UPPERCASE_LETTERS.findall(name)) >= 3:
        raise forms.ValidationError("Zu viele Großbuchstaben im Namen.")
