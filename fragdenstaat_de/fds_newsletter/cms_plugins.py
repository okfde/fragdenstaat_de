from django.utils.translation import gettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import NewsletterCMSPlugin
from .templatetags.newsletter_tags import get_newsletter_context


@plugin_pool.register_plugin
class NewsletterPlugin(CMSPluginBase):
    module = _("Newsletter")
    name = _('Newsletter Formular')
    model = NewsletterCMSPlugin
    cache = True
    text_enabled = True
    render_template = "fds_newsletter/plugins/newsletter_form.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context['newsletter'] = instance.newsletter
        return context


@plugin_pool.register_plugin
class SmartNewsletterPlugin(CMSPluginBase):
    module = _("Newsletter")
    name = _('Smart Newsletter Formular')
    model = NewsletterCMSPlugin
    cache = False
    text_enabled = True
    render_template = "fds_newsletter/plugins/smart_newsletter_form.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update(
            get_newsletter_context(
                context, newsletter=instance.newsletter, fallback=False
            )
        )
        return context
