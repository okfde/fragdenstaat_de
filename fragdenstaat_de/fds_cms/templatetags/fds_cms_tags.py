from django import template

from cms.plugin_rendering import ContentRenderer
from cms.models import StaticPlaceholder

register = template.Library()


@register.simple_tag(takes_context=True)
def fds_static_placeholder(context, code):
    static_placeholder = StaticPlaceholder.objects.get(
        code=code,
        site_id__isnull=True
    )
    placeholder = static_placeholder.public
    request = context['request']
    renderer = ContentRenderer(request=request)
    content = renderer.render_placeholder(
        placeholder,
        context=context,
        nodelist=None,
        editable=False,
        use_cache=True
    )
    return content
