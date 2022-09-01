from django import template

from ...fds_fximport.helper import IMPORTED_TAG, is_frontex_msg
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


@register.filter
def needs_frontex_import(message, user):
    if IMPORTED_TAG in message.tag_set:
        return False
    return is_frontex_msg(message)
