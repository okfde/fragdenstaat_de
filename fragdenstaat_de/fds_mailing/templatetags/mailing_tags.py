from django import template
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from ..models import MailingMessage

register = template.Library()


@register.filter
def get_mailingmessages(obj):
    ct = ContentType.objects.get_for_model(obj)
    filt = Q(
        mailingmessagereference__content_type=ct,
        mailingmessagereference__object_id=obj.pk,
    )
    if str(obj.__class__) == "Donor":
        filt |= Q(donor=obj)
    elif str(obj.__class__) == "Subscriber":
        filt |= Q(subscriber=obj)
    elif str(obj.__class__) == "User":
        filt |= Q(user=obj)
    return MailingMessage.objects.filter(filt).select_related("mailing")
