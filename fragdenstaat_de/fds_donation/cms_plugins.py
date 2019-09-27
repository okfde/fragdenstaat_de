from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import DonationGiftFormCMSPlugin
from .forms import DonationGiftForm


@plugin_pool.register_plugin
class DonationGiftFormPlugin(CMSPluginBase):
    model = DonationGiftFormCMSPlugin
    module = _("Donations")
    name = _("Donation Gift Form")
    text_enabled = True
    render_template = "fds_donation/cms_plugins/donationgiftform.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)

        context['category'] = instance.category
        initial = {}
        if context.get('request') and context['request'].user.is_authenticated:
            user = context['request'].user
            initial = {
                'name': user.get_full_name(),
                'email': user.email,
            }
        context['form'] = DonationGiftForm(
            category=instance.category,
            initial=initial
        )

        return context
