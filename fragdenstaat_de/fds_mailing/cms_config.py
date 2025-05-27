from django.template.response import TemplateResponse

from cms.app_base import CMSAppConfig

from .forms import PreviewMailingForm
from .models import EmailTemplate


def render_emailtemplate(request, emailtemplate: EmailTemplate):
    template = "fds_mailing/emailtemplate_update_form.html"
    preview_form = PreviewMailingForm.from_request(emailtemplate, request)
    email_context = {}
    if preview_form.is_valid():
        email_context = preview_form.get_context()
    render_error = None
    try:
        email_content = emailtemplate.get_email_content(email_context, preview=True)
    except Exception as e:
        render_error = str(e)
        email_content = None
    context = {
        "object": emailtemplate,
        "force_cms_render": True,
        "preview_mailing_form": preview_form,
        "email_content": email_content,
        "render_error": render_error,
    }
    return TemplateResponse(request, template, context)


class EmailTemplateCMSConfig(CMSAppConfig):
    cms_enabled = True
    cms_toolbar_enabled_models = [(EmailTemplate, render_emailtemplate)]
