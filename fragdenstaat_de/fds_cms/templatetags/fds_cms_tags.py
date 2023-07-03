from django import template
from django.conf import settings

from cms.models import StaticPlaceholder

from ..responsive_images import (
    get_filer_thumbnails,
    get_picture_plugin_column_sizes,
    get_responsive_image,
    parse_colsizes,
)
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


def thumbnail_dims(picture_plugin, default_width=768):
    if picture_plugin.width and picture_plugin.height:
        return (picture_plugin.width, picture_plugin.height)
    elif picture_plugin.height:
        return (0, picture_plugin.height)
    elif picture_plugin.width:
        return (picture_plugin.width, 0)
    return (default_width, 0)


@register.simple_tag
def get_responsive_plugin_image(picture_plugin):
    if picture_plugin.width or picture_plugin.height:
        thumbnails = get_filer_thumbnails(
            picture_plugin.picture,
            sizes=[(settings.THUMBNAIL_DEFAULT_ALIAS, thumbnail_dims(picture_plugin))],
            include_original=False,
            extra_opts={"crop": "scale"},
        )
    else:
        thumbnails = get_filer_thumbnails(picture_plugin.picture)

    column_sizes = get_picture_plugin_column_sizes(picture_plugin)
    return get_responsive_image(thumbnails, column_sizes)


@register.simple_tag
def get_responsive_filer_image(filer_image, column_classes):
    thumbnails = get_filer_thumbnails(filer_image)
    column_sizes = parse_colsizes(column_classes)
    return get_responsive_image(thumbnails, column_sizes)


@register.filter
def get_soft_root(page):
    if page.soft_root:
        return page
    soft_root = page.get_ancestor_pages().filter(soft_root=True).reverse().first()
    if soft_root:
        return soft_root
    return page.get_root()
