from django.utils.translation import ugettext_lazy as _
from django.urls import reverse

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import Donor, DonationGiftFormCMSPlugin, DonationFormCMSPlugin
from .forms import DonationGiftForm


@plugin_pool.register_plugin
class DonationGiftFormPlugin(CMSPluginBase):
    model = DonationGiftFormCMSPlugin
    module = _("Donations")
    name = _("Donation Gift Form")
    text_enabled = True
    cache = False
    render_template = "fds_donation/cms_plugins/donationgiftform.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)

        context['category'] = instance.category
        context['next_url'] = instance.next_url

        if not instance.next_url and context.get('request'):
            context['next_url'] = context['request'].get_full_path()

        initial = {}
        if context.get('request') and context['request'].user.is_authenticated:
            user = context['request'].user
            initial = {
                'name': user.get_full_name(),
                'email': user.email,
                'address': user.address,
            }
        context['form'] = DonationGiftForm(
            request=context.get('request'),
            category=instance.category,
            initial=initial
        )

        return context


@plugin_pool.register_plugin
class DonationFormPlugin(CMSPluginBase):
    model = DonationFormCMSPlugin
    module = _("Donations")
    name = _("Donation Form")
    text_enabled = True
    cache = False
    render_template = "fds_donation/forms/_form_wrapper.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        request = context['request']
        context['object'] = instance
        context['form'] = instance.make_form(
            user=request.user,
            reference=request.GET.get('pk_campaign', ''),
            keyword=request.GET.get('pk_keyword',
                                    request.META.get('HTTP_REFERER', '')),
            action=instance.form_action or reverse('fds_donation:donate')
        )
        return context


class DonorLogigMixin:
    module = _("Donations")
    cache = False
    allow_children = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        if 'donor' not in context:
            if 'user' not in context and 'request' in context:
                if context['request'].user.is_authenticated:
                    context['user'] = context['request'].user
            if 'user' in context and context['user'].is_authenticated:
                donors = Donor.objects.filter(user=context['user'])
                if donors:
                    context['donor'] = donors[0]

        context['is_donor'] = 'donor' in context
        return context


@plugin_pool.register_plugin
class IsDonorPlugin(DonorLogigMixin, CMSPluginBase):
    name = _("Is donor")
    render_template = "fds_donation/cms_plugins/is_donor.html"


@plugin_pool.register_plugin
class IsNotDonorPlugin(DonorLogigMixin, CMSPluginBase):
    name = _("Is donor")
    render_template = "fds_donation/cms_plugins/is_not_donor.html"


@plugin_pool.register_plugin
class IsRecurringDonorPlugin(DonorLogigMixin, CMSPluginBase):
    name = _("Is recurring donor")
    render_template = "fds_donation/cms_plugins/is_recurring_donor.html"


@plugin_pool.register_plugin
class IsNotRecurringDonorPlugin(DonorLogigMixin, CMSPluginBase):
    name = _("Is not recurring donor")
    render_template = "fds_donation/cms_plugins/is_not_recurring_donor.html"


@plugin_pool.register_plugin
class IsRecentDonor(DonorLogigMixin, CMSPluginBase):
    name = _("Is recent donor")
    render_template = "fds_donation/cms_plugins/is_recent_donor.html"


@plugin_pool.register_plugin
class IsNotRecentDonor(DonorLogigMixin, CMSPluginBase):
    name = _("Is not recent donor")
    render_template = "fds_donation/cms_plugins/is_not_recent_donor.html"
