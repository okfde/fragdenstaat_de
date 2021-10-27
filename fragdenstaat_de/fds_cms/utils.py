"""
Adapted from

https://github.com/divio/aldryn-search/blob/master/aldryn_search/helpers.py

"""

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.conf import settings

from cms.toolbar.toolbar import CMSToolbar
from cms.plugin_rendering import ContentRenderer


def get_plugin_children(instance):
    return (
        instance.get_descendants().filter(depth=instance.depth + 1).order_by("position")
    )


def get_request(language=None, path="/"):
    request_factory = RequestFactory()
    request = request_factory.get(path)
    request.session = {}
    request.LANGUAGE_CODE = language or settings.LANGUAGE_CODE

    # Needed for plugin rendering.
    request.current_page = None
    request.user = AnonymousUser()
    request.toolbar = CMSToolbar(request)
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
