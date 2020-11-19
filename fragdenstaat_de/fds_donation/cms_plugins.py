from django.db.models import Sum

from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from fragdenstaat_de.fds_mailing.utils import get_plugin_children

from .models import (Donor, DonationGiftFormCMSPlugin, DefaultDonation,
                     DonationFormCMSPlugin, DonationProgressBarCMSPlugin)
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
    render_template = "fds_donation/cms_plugins/donor_logic.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context = self.add_to_context(context)
        context['should_render'] = self.should_render(context)
        return context

    def add_to_context(self, context):
        if not context.get('donor'):
            if not context.get('user') and context.get('request'):
                if context['request'].user.is_authenticated:
                    context['user'] = context['request'].user
            if context.get('user') and context['user'].is_authenticated:
                donors = Donor.objects.filter(user=context['user'])
                if donors:
                    context['donor'] = donors[0]
        return context

    def should_render(self):
        raise NotImplementedError

    def render_text(self, context, instance):
        from fragdenstaat_de.fds_mailing.utils import render_plugin_text
        context = self.add_to_context(context)

        if self.should_render(context):
            children = get_plugin_children(instance)
            return '\n\n'.join(
                render_plugin_text(context, c) for c in children
            ).strip()
        return ''


@plugin_pool.register_plugin
class IsDonorPlugin(DonorLogigMixin, CMSPluginBase):
    name = _("Is donor")

    def should_render(self, context):
        return context.get('donor')


@plugin_pool.register_plugin
class IsNotDonorPlugin(DonorLogigMixin, CMSPluginBase):
    name = _("Is donor")

    def should_render(self, context):
        return not context.get('donor')


@plugin_pool.register_plugin
class IsRecurringDonorPlugin(DonorLogigMixin, CMSPluginBase):
    name = _("Is recurring donor")

    def should_render(self, context):
        return context.get('donor') and context['donor'].recurring_amount


@plugin_pool.register_plugin
class IsNotRecurringDonorPlugin(DonorLogigMixin, CMSPluginBase):
    name = _("Is not recurring donor")

    def should_render(self, context):
        return not context.get('donor') or not context['donor'].recurring_amount


@plugin_pool.register_plugin
class IsRecentDonor(DonorLogigMixin, CMSPluginBase):
    name = _("Is recent donor")

    def should_render(self, context):
        return context.get('donor') and context['donor'].recently_donated


@plugin_pool.register_plugin
class IsNotRecentDonor(DonorLogigMixin, CMSPluginBase):
    name = _("Is not recent donor")

    def should_render(self, context):
        return not context.get('donor') or not context['donor'].recently_donated


@plugin_pool.register_plugin
class ConcactAllowedDonor(DonorLogigMixin, CMSPluginBase):
    name = _("Is contact allowed donor")

    def should_render(self, context):
        return context.get('donor') and context['donor'].contact_allowed


@plugin_pool.register_plugin
class ConcactNotAllowedDonor(DonorLogigMixin, CMSPluginBase):
    name = _("Is contact not allowed donor")

    def should_render(self, context):
        return not context.get('donor') or not context['donor'].contact_allowed


@plugin_pool.register_plugin
class DonationProgressBarPlugin(CMSPluginBase):
    model = DonationProgressBarCMSPlugin
    module = _("Donations")
    name = _("Donation Progress Bar")
    text_enabled = True
    cache = False
    render_template = "fds_donation/cms_plugins/donation_progress_bar.html"

    def get_donation_count(self, instance):
        date = instance.start_date
        donation_goal = instance.donation_goal
        count = DefaultDonation.objects.filter(
            timestamp__gte=date
        ).aggregate(Sum('amount'))

        amount = count.get('amount__sum', 0)
        if amount and amount > donation_goal:
            amount = donation_goal
        perc = min(int(amount / donation_goal * 100), 100)
        return amount, perc

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        amount, perc = self.get_donation_count(instance)
        context['amount'] = amount
        context['percentage'] = perc
        return context
