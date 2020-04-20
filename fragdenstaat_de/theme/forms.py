import re
import logging

from django import forms
from django.contrib.gis.geoip2 import GeoIP2

from froide.helper.utils import get_client_ip

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
            validate_not_too_many_uppercase(form.cleaned_data['first_name'])
            validate_not_too_many_uppercase(form.cleaned_data['last_name'])
        except forms.ValidationError as e:
            logger.exception(e)
            raise
        if form.request:
            try:
                g = GeoIP2()
                info = g.country(get_client_ip(form.request))
                if info['country_code'] not in ('DE', 'CH', 'AT'):
                    logger.error('Signup from non-German speaking IP.', extra={
                        'request': form.request
                    })
            except Exception as e:
                logger.exception(e)

    def on_save(self, form, user):
        pass
