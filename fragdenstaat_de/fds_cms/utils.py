"""
Adapted from

https://github.com/divio/aldryn-search/blob/master/aldryn_search/helpers.py

"""

from typing import Optional

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from cms.models import CMSPlugin, Placeholder
from cms.plugin_rendering import ContentRenderer
from djangocms_alias.models import Alias


def get_plugin_children(instance):
    return CMSPlugin.objects.filter(parent=instance).order_by("position")


def get_request(language=None, path="/"):
    from cms.toolbar.toolbar import CMSToolbar

    request_factory = RequestFactory()
    request = request_factory.get(path)
    request.session = {}
    request.LANGUAGE_CODE = language or settings.LANGUAGE_CODE

    # Needed for plugin rendering.
    request.current_page = None
    request.user = AnonymousUser()
    toolbar = CMSToolbar(request)
    request.toolbar = toolbar
    return request


def clean_join(separator, iterable):
    """
    Filters out iterable to only join non empty items.
    """
    return separator.join(filter(None, iterable))


def render_placeholder(context, placeholder, use_cache=False):
    request = context.get("request")
    if request is None:
        return ""
    renderer = ContentRenderer(request=request)
    content = renderer.render_placeholder(
        placeholder, context=context, nodelist=None, editable=False, use_cache=use_cache
    )
    return content


def concat_classes(classes):
    """
    merges a list of classes and return concatinated string
    """
    return " ".join(_class for _class in classes if _class)


def get_alias_placeholder(
    alias_name: str, language: Optional[str] = None
) -> Optional[Placeholder]:
    alias = Alias.objects.filter(static_code=alias_name).first()
    if not alias:
        return ""
    if language is None:
        language = settings.LANGUAGE_CODE
    return alias.get_placeholder(language=language, show_draft_content=False)
