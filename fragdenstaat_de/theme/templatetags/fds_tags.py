from django import template

from ..glyphosat import FILENAME

register = template.Library()


@register.filter
def needs_glyphosat_attachment(message):
    if not (
        message.request.campaign_id == 9
        and message.is_response
        and "Kennwort lautet:" in message.plaintext
    ):
        return False
    if any(a.name == FILENAME for a in message.attachments):
        return False
    return True
