from django import template

from cms.models import StaticPlaceholder

from ..utils import render_placeholder

register = template.Library()


@register.filter
def is_campaign(obj, campaign):
    return obj.reference.startswith(campaign)


@register.simple_tag(takes_context=True)
def fds_static_placeholder(context, code):
    try:
        static_placeholder = StaticPlaceholder.objects.get(
            code=code, site_id__isnull=True
        )
    except StaticPlaceholder.DoesNotExist:
        return ""
    placeholder = static_placeholder.public
    return render_placeholder(context, placeholder, use_cache=True)


@register.filter
def thumbnail_dims(instance, default_width=768):
    if instance.width and instance.height:
        return "%dx%d" % (instance.width, instance.height)
    elif instance.height:
        return "0x%d" % instance.height
    elif instance.width:
        return "%dx0" % instance.width
    return "%dx0" % default_width
