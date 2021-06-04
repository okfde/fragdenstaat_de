import json

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NewsletterConfig(AppConfig):
    name = 'fragdenstaat_de.fds_newsletter'
    verbose_name = _('Newsletter FragDenStaat')

    def ready(self):
        from froide.account import (
            account_canceled, account_activated, account_merged,
            account_email_changed
        )
        from froide.account.export import registry
        from froide.account.forms import user_extra_registry
        from froide.bounce.signals import email_bounced, email_unsubscribed
        from froide.foirequestfollower.models import FoiRequestFollower

        from .forms import (
            NewsletterUserExtra, NewsletterFollowExtra
        )
        from .listeners import (
            activate_newsletter_subscription, user_email_changed,
            merge_user, cancel_user, subscribe_follower,
            handle_bounce, handle_unsubscribe
        )

        account_canceled.connect(cancel_user)
        account_merged.connect(merge_user)
        account_email_changed.connect(user_email_changed)
        account_activated.connect(activate_newsletter_subscription)
        email_bounced.connect(handle_bounce)
        email_unsubscribed.connect(handle_unsubscribe)
        user_extra_registry.register('registration', NewsletterUserExtra())
        user_extra_registry.register('follow', NewsletterFollowExtra())
        FoiRequestFollower.followed.connect(subscribe_follower)

        registry.register(export_user_data)


def export_user_data(user):
    from .models import Subscriber

    subscriptions = (
        Subscriber.objects
        .filter(user=user)
        .select_related('newsletter')
    )
    if subscriptions:
        yield ('newsletter_subscriptions.json', json.dumps([
            {
                'name': s.get_name(),
                'email': s.get_email(),
                'create_date': s.create_date.isoformat(),
                'subscribe_date': (
                    s.subscribed.isoformat()
                    if s.subscribed else None
                ),
                'unsubscribe_date': (
                    s.unsubscribed.isoformat()
                    if s.unsubscribed else None
                ),
                'newsletter': s.newsletter.title
            }
            for s in subscriptions]).encode('utf-8')
        )

