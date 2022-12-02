from decimal import Decimal

from django.db.models import Sum
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from fragdenstaat_de.fds_cms.utils import get_plugin_children

from .models import (
    DefaultDonation,
    DonationFormCMSPlugin,
    DonationGiftFormCMSPlugin,
    DonationProgressBarCMSPlugin,
    Donor,
)


@plugin_pool.register_plugin
class DonationGiftFormPlugin(CMSPluginBase):
    model = DonationGiftFormCMSPlugin
    module = _("Donations")
    name = _("Donation Gift Form")
    text_enabled = True
    cache = False
    render_template = "fds_donation/cms_plugins/donationgiftform.html"

    def render(self, context, instance, placeholder):
        from .forms import DonationGiftForm

        context = super().render(context, instance, placeholder)

        context["category"] = instance.category
        context["next_url"] = instance.next_url

        if not instance.next_url and context.get("request"):
            context["next_url"] = context["request"].get_full_path()

        initial = {}
        if context.get("request") and context["request"].user.is_authenticated:
            user = context["request"].user
            initial = {
                "name": user.get_full_name(),
                "email": user.email,
                "address": user.address,
            }
        context["form"] = DonationGiftForm(
            request=context.get("request"), category=instance.category, initial=initial
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
        request = context["request"]
        context["object"] = instance
        context["form"] = instance.make_form(
            user=request.user,
            request=request,
            reference=request.GET.get("pk_campaign", ""),
            keyword=request.GET.get("pk_keyword", request.META.get("HTTP_REFERER", "")),
            action=instance.form_action or reverse("fds_donation:donate"),
        )
        return context


class DonorLogicMixin:
    module = _("Donations")
    cache = False
    allow_children = True
    render_template = "fds_donation/cms_plugins/donor_logic.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context = self.add_to_context(context)
        context["should_render"] = self.should_render(context)
        return context

    def add_to_context(self, context):
        if not context.get("donor"):
            if not context.get("user") and context.get("request"):
                if context["request"].user.is_authenticated:
                    context["user"] = context["request"].user
            if context.get("user") and context["user"].is_authenticated:
                donors = Donor.objects.filter(user=context["user"])
                if donors:
                    context["donor"] = donors[0]
        return context

    def should_render(self):
        raise NotImplementedError

    def render_text(self, context, instance):
        from fragdenstaat_de.fds_mailing.utils import render_plugin_text

        context = self.add_to_context(context)

        if self.should_render(context):
            children = get_plugin_children(instance)
            return "\n\n".join(render_plugin_text(context, c) for c in children).strip()
        return ""


@plugin_pool.register_plugin
class IsDonorPlugin(DonorLogicMixin, CMSPluginBase):
    name = _("Is donor")

    def should_render(self, context):
        return context.get("donor")


@plugin_pool.register_plugin
class IsNotDonorPlugin(DonorLogicMixin, CMSPluginBase):
    name = _("Is not donor")

    def should_render(self, context):
        return not context.get("donor")


@plugin_pool.register_plugin
class IsRecurringDonorPlugin(DonorLogicMixin, CMSPluginBase):
    name = _("Is recurring donor")

    def should_render(self, context):
        return context.get("donor") and context["donor"].recurring_amount


@plugin_pool.register_plugin
class IsNotRecurringDonorPlugin(DonorLogicMixin, CMSPluginBase):
    name = _("Is not recurring donor")

    def should_render(self, context):
        return not context.get("donor") or not context["donor"].recurring_amount


@plugin_pool.register_plugin
class IsRecentDonor(DonorLogicMixin, CMSPluginBase):
    name = _("Is recent donor")

    def should_render(self, context):
        return context.get("donor") and context["donor"].recently_donated


@plugin_pool.register_plugin
class IsNotRecentDonor(DonorLogicMixin, CMSPluginBase):
    name = _("Is not recent donor")

    def should_render(self, context):
        return not context.get("donor") or not context["donor"].recently_donated


@plugin_pool.register_plugin
class ConcactAllowedDonor(DonorLogicMixin, CMSPluginBase):
    name = _("Is contact allowed donor")

    def should_render(self, context):
        return context.get("donor") and context["donor"].contact_allowed


@plugin_pool.register_plugin
class ConcactNotAllowedDonor(DonorLogicMixin, CMSPluginBase):
    name = _("Is contact not allowed donor")

    def should_render(self, context):
        return not context.get("donor") or not context["donor"].contact_allowed


@plugin_pool.register_plugin
class DonationProgressBarPlugin(CMSPluginBase):
    model = DonationProgressBarCMSPlugin
    module = _("Donations")
    name = _("Donation Progress Bar")
    text_enabled = True
    cache = False
    render_template = "fds_donation/cms_plugins/donation_progress_bar.html"

    def get_percentage(self, amount, max):
        if amount > 0 and max > 0:
            return min(int(amount / max * 100), 100)
        return 0

    def get_donated_amount(self, instance):
        if instance.received_donations_only:
            qs = DefaultDonation.objects.estimate_received_donations(
                instance.start_date
            )
        else:
            qs = DefaultDonation.objects.filter(
                completed=True, timestamp__gte=instance.start_date
            )

        total_sum = qs.aggregate(amount=Sum("amount"))["amount"]

        return total_sum or Decimal(0.0)

    def get_donation_goal_perc(self, instance, donated_amount):
        donation_goal = instance.donation_goal
        reached_goal = instance.reached_goal

        if donated_amount and donated_amount > 0 and donation_goal > 0:
            if donation_goal >= donated_amount:
                if reached_goal and donated_amount > reached_goal:
                    donated_amount = donated_amount - reached_goal
                perc = self.get_percentage(donated_amount, donation_goal)
            else:
                if reached_goal and donation_goal > reached_goal:
                    donation_goal = donation_goal - reached_goal
                perc = self.get_percentage(donation_goal, donated_amount)
            return perc
        return 0

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        donated_amount = self.get_donated_amount(instance)
        donated_amount_perc = self.get_donation_goal_perc(instance, donated_amount)

        context["amount"] = donated_amount
        context["percentage"] = donated_amount_perc
        context["donation_goal"] = instance.donation_goal
        context["white_text"] = instance.white_text

        if instance.reached_goal and instance.reached_goal < donated_amount:
            context["reached_goal"] = instance.reached_goal
            context["reached_goal_perc"] = self.get_percentage(
                instance.reached_goal, instance.donation_goal
            )

        return context
