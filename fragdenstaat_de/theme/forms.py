import re
import logging

from django import forms

logger = logging.getLogger(__name__)

UPPERCASE_LETTERS = re.compile(r'[A-Z]')


def validate_not_too_many_uppercase(name):
    if ' ' in name:
        return
    if len(UPPERCASE_LETTERS.findall(name)) >= 3:
        raise forms.ValidationError('Zu viele Großbuchstaben im Namen.')


class SignupUserCheckExtra():
    def on_init(self, form):
        pass

    def on_clean(self, form):
        try:
            if 'first_name' in form.cleaned_data:
                validate_not_too_many_uppercase(form.cleaned_data['first_name'])
            if 'last_name' in form.cleaned_data:
                validate_not_too_many_uppercase(form.cleaned_data['last_name'])
        except forms.ValidationError:
            raise

    def on_save(self, form, user):
        pass
