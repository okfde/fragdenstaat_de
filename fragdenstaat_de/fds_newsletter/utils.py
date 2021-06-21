from datetime import timedelta
import hashlib

from django.conf import settings
from django.utils import timezone

from .models import Newsletter, Subscriber


class SubscriptionResult:
    ALREADY_SUBSCRIBED = 0
    SUBSCRIBED = 1
    CONFIRM = 2


def unsubscribe_queryset(subscribers, method=''):
    subscribers.update(
        subscribed=None,
        unsubscribed=timezone.now(),
        unsubscribe_method=method
    )


def subscribe_to_default_newsletter(email, user=None, **kwargs):
    return subscribe_to_newsletter(
        settings.DEFAULT_NEWSLETTER,
        email,
        user=user,
        **kwargs
    )


def subscribe_to_newsletter(slug, email, user=None, **kwargs):
    try:
        newsletter = Newsletter.objects.get(
            slug=slug
        )
    except Newsletter.DoesNotExist:
        return
    return subscribe(
        newsletter, email,
        user=user,
        **kwargs
    )


def subscribe(newsletter, email, user=None, name='', email_confirmed=False,
              reference='', keyword=''):
    if user and not user.is_authenticated:
        user = None
    if user and not user.is_active:
        # if user is not active, we have no confirmed address
        user = None

    if user and user.email.lower() == email.lower():
        email_confirmed = True

    if user and email_confirmed:
        return subscribe_user(
            newsletter, user, reference=reference, keyword=keyword
        )
    return subscribe_email(
        newsletter, email,
        email_confirmed=email_confirmed,
        name=name,
        reference=reference, keyword=keyword
    )


def subscribe_email(newsletter, email, email_confirmed=False, name='',
                    reference='', keyword=''):
    subscriber, created = Subscriber.objects.get_or_create(
        email=email.lower(),
        newsletter=newsletter,
        defaults={
            'name': name,
            'reference': reference,
            'keyword': keyword
        }
    )

    if subscriber.subscribed:
        subscriber.send_already_email()
        return (SubscriptionResult.ALREADY_SUBSCRIBED, subscriber)
    if not email_confirmed:
        subscriber.send_activation_email()
        return (SubscriptionResult.CONFIRM, subscriber)

    subscriber.subscribe(reference=reference, keyword=keyword)
    return (SubscriptionResult.SUBSCRIBED, subscriber)


def subscribe_user(newsletter, user, reference='', keyword='') -> bool:
    subscriber, created = Subscriber.objects.get_or_create(
        newsletter=newsletter, user=user,
        defaults={
            'reference': reference,
            'keyword': keyword
        }
    )
    if subscriber.subscribed:
        return (SubscriptionResult.ALREADY_SUBSCRIBED, subscriber)

    subscriber.subscribe(reference=reference, keyword=keyword)
    return (SubscriptionResult.SUBSCRIBED, subscriber)


def has_newsletter(user, newsletter_slug=None):
    if not user.is_authenticated:
        return None
    try:
        newsletter = Newsletter.objects.get(
            slug=newsletter_slug or settings.DEFAULT_NEWSLETTER
        )
    except Newsletter.DoesNotExist:
        return None

    return Subscriber.objects.filter(
        newsletter=newsletter, user=user, subscribed__isnull=False
    ).exists()


def cleanup_subscribers():
    now = timezone.now()
    month_ago = now - timedelta(days=30)
    three_days_ago = now - timedelta(days=3)

    # Unconfirmed subscribers older than 30 days
    Subscriber.objects.filter(
        created__lt=month_ago,
        subscribed=None,
        unsubscribed=None
    ).delete()

    # Unsubscribed more than 30 days ago
    Subscriber.objects.filter(
        unsubscribed__lt=month_ago
    ).delete()

    # Recently unsubscribed: anonymize data
    # but keep to prove recent existence
    subs = Subscriber.objects.filter(
        unsubscribed__lt=three_days_ago,
        email_hash=''
    )
    for sub in subs:
        m = hashlib.sha256()
        m.update(sub.get_email().lower().encode('utf-8'))
        sub.email_hash = m.hexdigest()
        sub.email = None
        sub.user = None
        sub.name = ''
        sub.save()
