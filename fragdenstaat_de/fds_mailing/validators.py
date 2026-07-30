from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_sender_domain(value):
    sender_domain = value.split("@", 1)[1]
    if sender_domain not in settings.SENDER_DOMAINS:
        raise ValidationError(_("Sender email needs to come from allowed domains."))
