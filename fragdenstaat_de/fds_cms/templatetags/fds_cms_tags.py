from django import template
from django.conf import settings

from cms.models import Page

from ..responsive_images import (
    ResponsiveImage,
    get_filer_thumbnails,
    get_picture_plugin_column_sizes,
    get_responsive_image,
    parse_colsizes,
)
from ..utils import get_alias_placeholder, render_placeholder

register = template.Library()


@register.filter
def is_campaign(obj, campaign):
    return obj.reference.startswith(campaign)


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
    if not picture_plugin.picture:
        return ResponsiveImage()
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
    if not filer_image:
        return ResponsiveImage()
    thumbnails = get_filer_thumbnails(filer_image)
    column_sizes = parse_colsizes(column_classes)
    return get_responsive_image(thumbnails, column_sizes)


@register.filter
def get_soft_root(page):
    if page.soft_root:
        return page
    soft_root = (
        page.get_ancestor_pages()
        .filter(pagecontent_set__soft_root=True)
        .reverse()
        .first()
    )
    if soft_root:
        return soft_root
    return page.get_root()


@register.simple_tag(takes_context=True)
def get_breadcrumb_ancestor(context, navigation_node):
    if navigation_node is None:
        return

    try:
        request = context["request"]
    except KeyError:
        return

    try:
        page = Page.objects.get(pk=navigation_node.id)
        ancestor = page.fdspageextension.breadcrumb_ancestor
        only_upwards = page.fdspageextension.ancestor_only_upwards
    except AttributeError:
        return

    if ancestor is None:
        return

    if only_upwards and request.current_page != page:
        return

    title = ancestor.get_title(language=request.LANGUAGE_CODE)
    url = ancestor.get_absolute_url(language=request.LANGUAGE_CODE)

    return {"title": title, "url": url}


@register.simple_tag(takes_context=True)
def fds_static_alias(context, alias_name):
    """
    Used because `static_alias` does not resolve variables in the alias name.
    TODO: remove when https://github.com/django-cms/djangocms-alias/pull/191
    is merged and released.
    """
    request = context["request"]
    placeholder = get_alias_placeholder(alias_name, request.LANGUAGE_CODE)
    if placeholder:
        return render_placeholder(context, placeholder)
    return ""
