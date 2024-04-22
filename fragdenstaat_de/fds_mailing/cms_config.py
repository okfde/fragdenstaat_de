from django.template.response import TemplateResponse

from cms.app_base import CMSAppConfig

from .models import EmailTemplate


def render_emailtemplate(request, emailtemplate):
    template = "fds_mailing/emailtemplate_update_form.html"
    context = {
        "object": emailtemplate,
        "force_cms_render": True,
    }
    return TemplateResponse(request, template, context)


class EmailTemplateCMSConfig(CMSAppConfig):
    cms_enabled = True
    cms_toolbar_enabled_models = [(EmailTemplate, render_emailtemplate)]
