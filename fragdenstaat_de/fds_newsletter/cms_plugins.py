from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from newsletter.models import Newsletter

from fragdenstaat_de.fds_mailing.models import Mailing


@plugin_pool.register_plugin
class NewsletterPlugin(CMSPluginBase):
    module = _("Newsletter")
    name = _('Newsletter Formular')
    cache = True
    text_enabled = True
    render_template = "fds_newsletter/plugins/newsletter_form.html"


@plugin_pool.register_plugin
class SmartNewsletterPlugin(CMSPluginBase):
    module = _("Newsletter")
    name = _('Smart Newsletter Formular')
    cache = False
    text_enabled = True
    render_template = "fds_newsletter/plugins/smart_newsletter.html"


@plugin_pool.register_plugin
class NewsletterArchivePlugin(CMSPluginBase):
    module = _("Newsletter")
    name = _('Newsletter Archive')
    cache = True
    text_enabled = False
    render_template = "fds_newsletter/plugins/archive.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context['newsletter'] = None
        try:
            context['newsletter'] = Newsletter.objects.get(
                slug=settings.DEFAULT_NEWSLETTER
            )
        except Newsletter.DoesNotExist:
            return context
        context['latest'] = Mailing.objects.filter(
            publish=True, ready=True, submitted=True,
            newsletter=context['newsletter']
        ).order_by('-sending_date')
        return context
