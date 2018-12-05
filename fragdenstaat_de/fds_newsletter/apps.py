from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class NewsletterConfig(AppConfig):
    name = 'fragdenstaat_de.fds_newsletter'
    verbose_name = _('Newsletter FragDenStaat')

    def ready(self):
        from froide.account import account_canceled, account_activated
        from froide.account.forms import user_extra_registry
        from froide.bounce.signals import email_bounced

        from .forms import NewsletterUserExtra
        from .utils import handle_bounce

        account_canceled.connect(cancel_user)
        account_activated.connect(activate_newsletter_subscription)
        email_bounced.connect(handle_bounce)
        user_extra_registry.register(NewsletterUserExtra())


def cancel_user(sender, user=None, **kwargs):
    from newsletter.models import Subscription

    if user is None:
        return

    Subscription.objects.filter(
        user=user,
        email_field__isnull=True,
    ).delete()

    # If user was previously subscribed, disconnect
    # but keeping subscription
    Subscription.objects.filter(
        user=user,
        email_field__isnull=False,
    ).update(user=None)


def activate_newsletter_subscription(sender, **kwargs):
    from .models import Subscription

    # Add user to existing newsletter subscriptions
    Subscription.objects.filter(
        email_field=sender.email,
        user__isnull=True
    ).update(user=sender)

    # Activate existing subscribers
    Subscription.objects.filter(
        user=sender,
        newsletter__slug=settings.DEFAULT_NEWSLETTER
    ).update(subscribed=True)
