import datetime
import logging
import re

from django import forms
from django.utils import timezone

from froide.account.models import UserPreference

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


BET_CHOICES = [
    ('bw', 'Baden-Württemberg'),
    ('by', 'Bayern'),
    ('be', 'Berlin'),
    ('bb', 'Brandenburg'),
    ('hb', 'Bremen'),
    ('hh', 'Hamburg'),
    ('he', 'Hessen'),
    ('mv', 'Mecklenburg-Vorpommern'),
    ('ni', 'Niedersachsen'),
    ('nw', 'Nordrhein-Westfalen'),
    ('rp', 'Rheinland-Pfalz'),
    ('sl', 'Saarland'),
    ('sn', 'Sachsen'),
    ('st', 'Sachsen-Anhalt'),
    ('sh', 'Schleswig-Holstein'),
    ('th', 'Thüringen'),
]


class TippspielForm(forms.Form):
    name = forms.CharField(max_length=50)
    match = forms.IntegerField(min_value=1, max_value=8)
    bet = forms.ChoiceField(choices=BET_CHOICES)

    def clean(self):
        deadline = datetime.datetime(2020, 6, 12, 12, 0, 0)
        deadline = timezone.get_current_timezone().localize(deadline)
        if timezone.now() >= deadline:
            raise forms.ValidationError('Tipp-Spiel-Runde abgelaufen!')

    def save(self, user):
        key = 'fds_meisterschaften_2020_name'
        UserPreference.objects.update_or_create(
            user=user, key=key,
            defaults={'value': self.cleaned_data['name']}
        )
        key = 'fds_meisterschaften_2020_{}'.format(self.cleaned_data['match'])
        UserPreference.objects.update_or_create(
            user=user, key=key,
            defaults={'value': self.cleaned_data['bet']}
        )
