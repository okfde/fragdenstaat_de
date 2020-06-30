from django.core.exceptions import PermissionDenied
from django.contrib.admin import helpers
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from froide.helper.text_utils import convert_html_to_text
from froide.helper.email_sending import send_mail
from froide.helper.forms import get_fake_fk_form_class


def add_style(instance, placeholder, context):
    return {
        'style': {
            'primary': '#3676ff',
            'light': '#d0d0d0'
        }
    }


def get_plugin_children(instance):
    return instance.get_descendants().filter(
        depth=instance.depth + 1).order_by('position')


def render_text(placeholder, context):
    plugins = placeholder.get_plugins()
    return '\n'.join(
        render_plugin_text(context, plugin) for plugin in plugins
        if plugin.depth == 1
    )


def render_plugin_text(context, base_plugin):
    instance, plugin = base_plugin.get_plugin_instance()
    if instance is None:
        return ''
    if hasattr(plugin, 'render_text'):
        return plugin.render_text(context, instance)
    if base_plugin.plugin_type == 'TextPlugin':
        return convert_html_to_text(instance.body, ignore_tags=('b', 'strong'))
    return ''


def send_template_email(email_template, context, **kwargs):
    content = email_template.get_email_content(context)
    user_email = kwargs.pop('user_email')
    kwargs['html'] = content.html
    return send_mail(
        content.subject, content.text, user_email,
        **kwargs
    )


def get_admin_url(obj):
    return reverse('admin:%s_%s_change' % (
        obj._meta.app_label, obj._meta.model_name
    ), args=[obj.pk])


class SetupMailingMixin:
    actions = ['setup_mailing']

    def setup_mailing_messages(self, mailing, queryset):
        raise NotImplementedError

    def setup_mailing(self, request, queryset):
        from .models import Mailing, EmailTemplate

        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        Form = get_fake_fk_form_class(EmailTemplate, self.admin_site)
        # User has already chosen the other req
        if request.POST.get('obj'):
            f = Form(request.POST)
            if f.is_valid():
                email_template = f.cleaned_data['obj']

                mailing = Mailing.objects.create(
                    name=email_template.name,
                    email_template=email_template
                )

                message = self.setup_mailing_messages(mailing, queryset)

                self.message_user(request, message)

                return redirect(get_admin_url(mailing))
        else:
            f = Form()

        context = {
            'opts': opts,
            'queryset': queryset,
            'media': self.media,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'form': f,
            'applabel': opts.app_label
        }

        # Display the confirmation page
        return TemplateResponse(request, 'admin/fds_mailing/mailing/send_mailing.html',
            context)
    setup_mailing.short_description = _("Prepare mailing to selected recipients...")
