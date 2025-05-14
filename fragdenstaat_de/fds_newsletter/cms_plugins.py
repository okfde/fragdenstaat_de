from django.conf import settings
from django.utils.translation import gettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import NewsletterCMSPlugin, Subscriber
from .templatetags.newsletter_tags import get_newsletter_context


@plugin_pool.register_plugin
class NewsletterPlugin(CMSPluginBase):
    module = _("Newsletter")
    name = _("Newsletter Formular")
    model = NewsletterCMSPlugin
    cache = True
    text_enabled = True
    render_template = "fds_newsletter/plugins/newsletter_form.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["newsletter"] = instance.newsletter
        return context


@plugin_pool.register_plugin
class SmartNewsletterPlugin(CMSPluginBase):
    module = _("Newsletter")
    name = _("Smart Newsletter Formular")
    model = NewsletterCMSPlugin
    cache = False
    text_enabled = True
    render_template = "fds_newsletter/plugins/smart_newsletter_form.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update(
            get_newsletter_context(
                context, newsletter=instance.newsletter, fallback=instance.fallback
            )
        )
        return context


class NewsletterLogicMixin:
    module = _("Newsletter")
    cache = False
    allow_children = True
    render_template = "fds_newsletter/plugins/newsletter_logic.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context = self.add_to_context(context)
        context["should_render"] = self.should_render(context)
        return context

    def add_to_context(self, context):
        """

        Show newsletter?

        is subscriber |	not a mailing	| mailing
            yes		  |	    n				n
            no 		  |     y				y
            unknown   |     y				n

        """
        mailing_link = False
        if context.get("request"):
            request = context["request"]
            campaign_tag = request.GET.get("pk_campaign")
            if campaign_tag and campaign_tag.startswith("mailing"):
                mailing_link = True
        if not context.get("user") and context.get("request"):
            if context["request"].user.is_authenticated:
                context["user"] = context["request"].user

        is_subscriber = None  # unknown by default
        if context.get("user") and context["user"].is_authenticated:
            subscribers = Subscriber.objects.filter(
                newsletter__slug=settings.DEFAULT_NEWSLETTER, user=context["user"]
            )
            if subscribers:
                context["subscriber"] = subscribers[0]
                is_subscriber = True
            else:
                # Definitely not a subscriber
                is_subscriber = False

        context["show_newsletter"] = is_subscriber is False or (
            not mailing_link and is_subscriber is None
        )
        return context

    def should_render(self):
        raise NotImplementedError


@plugin_pool.register_plugin
class IsNewsletterSubscriberPlugin(NewsletterLogicMixin, CMSPluginBase):
    name = _("Is newsletter subscriber")

    def should_render(self, context):
        return not context["show_newsletter"]


@plugin_pool.register_plugin
class IsNotNewsletterSubscriberPlugin(NewsletterLogicMixin, CMSPluginBase):
    name = _("Is not newsletter subscriber")

    def should_render(self, context):
        return context["show_newsletter"]
