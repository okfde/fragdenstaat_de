import json

from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class NewsletterConfig(AppConfig):
    name = "fragdenstaat_de.fds_newsletter"
    verbose_name = _("Newsletter FragDenStaat")

    def ready(self):
        from froide.account import (
            account_activated,
            account_canceled,
            account_email_changed,
            account_merged,
        )
        from froide.account.export import registry
        from froide.account.forms import user_extra_registry
        from froide.bounce.signals import email_bounced, email_unsubscribed
        from froide.foirequestfollower.models import FoiRequestFollower

        from . import subscribed
        from .forms import NewsletterFollowExtra, NewsletterUserExtra
        from .listeners import (
            activate_newsletter_subscription,
            cancel_user,
            handle_bounce,
            handle_unsubscribe,
            merge_user,
            send_welcome_mail,
            subscribe_follower,
            user_email_changed,
        )

        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        account_email_changed.connect(user_email_changed)
        account_activated.connect(activate_newsletter_subscription)
        email_bounced.connect(handle_bounce)
        email_unsubscribed.connect(handle_unsubscribe)
        subscribed.connect(send_welcome_mail)
        user_extra_registry.register("registration", NewsletterUserExtra())
        user_extra_registry.register("follow", NewsletterFollowExtra())
        FoiRequestFollower.followed.connect(subscribe_follower)

        registry.register(export_user_data)

        setup_newsletter_mails()


def setup_newsletter_mails():
    from froide.helper.email_sending import mail_registry

    NL_CONTEXT_VARS = ("subscriber", "newsletter")

    welcome = getattr(settings, "NEWSLETTER_WELCOME_MAILINTENT", None)
    if welcome:
        mail_registry.register(welcome, NL_CONTEXT_VARS)
    schedule = getattr(settings, "NEWSLETTER_ONBOARDING_SCHEDULE", [])
    for item in schedule:
        if item["mail_intent"]:
            mail_registry.register(item["mail_intent"], NL_CONTEXT_VARS)


def export_user_data(user):
    from .models import Subscriber

    subscriptions = Subscriber.objects.filter(user=user).select_related("newsletter")
    if subscriptions:
        yield (
            "newsletter_subscriptions.json",
            json.dumps(
                [
                    {
                        "name": s.get_name(),
                        "email": s.get_email(),
                        "create_date": s.created.isoformat(),
                        "subscribe_date": (
                            s.subscribed.isoformat() if s.subscribed else None
                        ),
                        "unsubscribe_date": (
                            s.unsubscribed.isoformat() if s.unsubscribed else None
                        ),
                        "newsletter": s.newsletter.title,
                        "reference": s.reference,
                        "keyword": s.keyword,
                    }
                    for s in subscriptions
                ]
            ).encode("utf-8"),
        )
