import json

from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


class NewsletterConfig(AppConfig):
    name = 'fragdenstaat_de.fds_newsletter'
    verbose_name = _('Newsletter FragDenStaat')

    def ready(self):
        from froide.account import account_canceled, account_activated, account_merged
        from froide.account.export import registry
        from froide.account.forms import user_extra_registry
        from froide.bounce.signals import email_bounced, email_unsubscribed

        from .forms import NewsletterUserExtra, DonorNewsletterExtra
        from .utils import handle_bounce, handle_unsubscribe

        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        account_activated.connect(activate_newsletter_subscription)
        email_bounced.connect(handle_bounce)
        email_unsubscribed.connect(handle_unsubscribe)
        user_extra_registry.register('registration', NewsletterUserExtra())
        user_extra_registry.register('donation', DonorNewsletterExtra())

        registry.register(export_user_data)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    from .models import Subscription

    old_subscribed = Subscription.objects.filter(
        user=old_user, email_field__isnull=True,
        subscribed=True
    ).exists()
    new_subscribed = Subscription.objects.filter(
        user=new_user, subscribed=True
    ).exists()
    if old_subscribed and not new_subscribed:
        new_exists = Subscription.objects.filter(
            user=new_user
        ).exists()
        if new_exists:
            Subscription.objects.filter(
                user=new_user
            ).update(subscribed=True)
        else:
            Subscription.objects.filter(
                user=old_user
            ).update(user=new_user)


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

    # TODO: make sure entries are related to user action

    # Add user to existing newsletter subscriptions
    Subscription.objects.filter(
        email_field=sender.email,
        user__isnull=True
    ).update(user=sender, email_field='')

    # Remove duplicates
    user_subs = Subscription.objects.filter(
        user=sender,
        newsletter__slug=settings.DEFAULT_NEWSLETTER
    )
    if user_subs.count() > 1:
        first = user_subs[0]
        user_subs.exclude(id=first.id).delete()

    # Activate existing subscribers
    Subscription.objects.filter(
        user=sender,
        newsletter__slug=settings.DEFAULT_NEWSLETTER
    ).update(subscribed=True)


def export_user_data(user):
    from newsletter.models import Subscription

    subscriptions = (
        Subscription.objects
        .filter(user=user,)
        .select_related('newsletter')
    )
    if subscriptions:
        yield ('newsletter_subscriptions.json', json.dumps([
            {
                'name': s.name,
                'email': s.email,
                'ip': str(s.ip),
                'create_date': s.create_date.isoformat(),
                'subscribed': s.subscribed,
                'subscribe_date': (
                    s.subscribe_date.isoformat()
                    if s.subscribe_date else None
                ),
                'unsubscribed': s.unsubscribed,
                'unsubscribe_date': (
                    s.unsubscribe_date.isoformat()
                    if s.unsubscribe_date else None
                ),
                'newsletter': s.newsletter.title
            }
            for s in subscriptions]).encode('utf-8')
        )
