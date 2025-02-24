from django.template.response import TemplateResponse

from cms.app_base import CMSAppConfig

from .models import Event


def render_event_content(request, event):
    template = "fds_events/event_detail.html"
    context = {
        "event": event,
        "force_cms_render": True,
        "CMS_TEMPLATE": "cms/blog_base.html",
    }
    return TemplateResponse(request, template, context)


class FdsEventsCMSConfig(CMSAppConfig):
    cms_enabled = True
    cms_toolbar_enabled_models = [(Event, render_event_content)]
