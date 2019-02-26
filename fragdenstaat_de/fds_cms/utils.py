'''
Adapted from

https://github.com/divio/aldryn-search/blob/master/aldryn_search/helpers.py

'''

from django.contrib.auth.models import AnonymousUser
from django.template import RequestContext, Engine
from django.test import RequestFactory
from django.utils.text import smart_split
from django.utils.encoding import force_text
from django.utils.html import strip_tags
from django.conf import settings

from cms.toolbar.toolbar import CMSToolbar
from cms.plugin_rendering import ContentRenderer


EXCLUDED_PLUGINS = getattr(settings, 'SEARCH_EXCLUDED_PLUGINS', [])


def _render_plugin(plugin, context, renderer=None):
    if renderer:
        content = renderer.render_plugin(
            instance=plugin,
            context=context,
            editable=False,
        )
    else:
        content = plugin.render_plugin(context)
    return content


def get_cleaned_bits(data):
    decoded = force_text(data)
    stripped = strip_tags(decoded)
    return smart_split(stripped)


def get_plugin_index_data(base_plugin, request):
    text_bits = []

    instance, plugin_type = base_plugin.get_plugin_instance()

    if instance is None or instance.plugin_type in EXCLUDED_PLUGINS:
        # this is an empty plugin or excluded from search
        return text_bits

    search_fields = getattr(instance, 'search_fields', [])
    if hasattr(instance, 'search_fulltext'):
        # check if the plugin instance has search enabled
        search_contents = instance.search_fulltext
    elif hasattr(base_plugin, 'search_fulltext'):
        # now check in the base plugin instance (CMSPlugin)
        search_contents = base_plugin.search_fulltext
    elif hasattr(plugin_type, 'search_fulltext'):
        # last check in the plugin class (CMSPluginBase)
        search_contents = plugin_type.search_fulltext
    else:
        # disabled if there's search fields defined,
        # otherwise it's enabled.
        search_contents = not bool(search_fields)

    if search_contents:
        context = RequestContext(request)
        updates = {}
        engine = Engine.get_default()

        for processor in engine.template_context_processors:
            updates.update(processor(context.request))
        context.dicts[context._processors_index] = updates

        try:
            # django-cms>=3.5
            renderer = request.toolbar.content_renderer
        except AttributeError:
            # django-cms>=3.4
            renderer = context.get('cms_content_renderer')

        plugin_contents = _render_plugin(instance, context, renderer)

        if plugin_contents:
            text_bits = get_cleaned_bits(plugin_contents)

    return text_bits


def get_request(language=None):
    """
    Returns a Request instance populated with cms specific attributes.
    """
    request_factory = RequestFactory(HTTP_HOST=settings.ALLOWED_HOSTS[0])
    request = request_factory.get("/")
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


def render_placeholder(context, placeholder):
    request = context.get('request')
    if request is None:
        return ''
    renderer = ContentRenderer(request=request)
    content = renderer.render_placeholder(
        placeholder,
        context=context,
        nodelist=None,
        editable=False,
        use_cache=True
    )
    return content
