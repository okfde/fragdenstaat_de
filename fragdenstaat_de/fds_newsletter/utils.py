import csv
import datetime
import hashlib
from datetime import timedelta
from enum import Enum
from typing import Tuple

from django.conf import settings
from django.db.models import Q
from django.db.models.functions import Collate
from django.utils import timezone

from froide.helper.email_sending import mail_registry

from .models import Newsletter, Subscriber


class SubscriptionResult(Enum):
    ALREADY_SUBSCRIBED = 0
    SUBSCRIBED = 1
    CONFIRM = 2


SubscriptionReturn = Tuple[SubscriptionResult, Subscriber]


def unsubscribe_queryset(subscribers, method=""):
    subscribers.update(
        subscribed=None, unsubscribed=timezone.now(), unsubscribe_method=method
    )


def subscribe_to_default_newsletter(email, user=None, **kwargs) -> SubscriptionReturn:
    return subscribe_to_newsletter(
        settings.DEFAULT_NEWSLETTER, email, user=user, **kwargs
    )


def subscribe_to_newsletter(slug, email, user=None, **kwargs) -> SubscriptionReturn:
    try:
        newsletter = Newsletter.objects.get(slug=slug)
    except Newsletter.DoesNotExist:
        return
    return subscribe(newsletter, email, user=user, **kwargs)


def subscribe(
    newsletter,
    email,
    user=None,
    name="",
    email_confirmed=False,
    reference="",
    keyword="",
) -> SubscriptionReturn:
    if user and not user.is_authenticated:
        user = None
    if user and not user.is_active:
        # if user is not active, we have no confirmed address
        user = None

    if user and user.email.lower() == email.lower():
        email_confirmed = True

    if user and email_confirmed:
        return subscribe_user(newsletter, user, reference=reference, keyword=keyword)
    return subscribe_email(
        newsletter,
        email,
        email_confirmed=email_confirmed,
        name=name,
        reference=reference,
        keyword=keyword,
    )


def subscribe_email(
    newsletter,
    email,
    email_confirmed=False,
    name="",
    reference="",
    keyword="",
    batch=False,
) -> SubscriptionReturn:
    try:
        Subscriber.objects.annotate(
            user_email_deterministic=Collate("user__email", "und-x-icu"),
        ).filter(Q(email=email.lower()) | Q(user_email_deterministic=email)).get(
            newsletter=newsletter
        )
    except Subscriber.DoesNotExist:
        subscriber, _created = Subscriber.objects.get_or_create(
            email=email.lower(),
            newsletter=newsletter,
            defaults={"name": name, "reference": reference, "keyword": keyword},
        )

    if subscriber.subscribed:
        return (SubscriptionResult.ALREADY_SUBSCRIBED, subscriber)
    if not email_confirmed:
        subscriber.send_activation_email(batch=batch)
        return (SubscriptionResult.CONFIRM, subscriber)

    subscriber = subscriber.subscribe(reference=reference, keyword=keyword, batch=batch)
    return (SubscriptionResult.SUBSCRIBED, subscriber)


def subscribe_user(newsletter, user, reference="", keyword="") -> SubscriptionReturn:
    try:
        subscriber = Subscriber.objects.filter(
            Q(email=user.email.lower()) | Q(user=user)
        ).get(newsletter=newsletter)
    except Subscriber.DoesNotExist:
        subscriber, _created = Subscriber.objects.get_or_create(
            newsletter=newsletter,
            user=user,
            defaults={"reference": reference, "keyword": keyword},
        )
    if subscriber.subscribed:
        return (SubscriptionResult.ALREADY_SUBSCRIBED, subscriber)

    subscriber = subscriber.subscribe(reference=reference, keyword=keyword)
    return (SubscriptionResult.SUBSCRIBED, subscriber)


def has_newsletter(user, newsletter_slug=None) -> bool:
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
        created__lt=month_ago, subscribed=None, unsubscribed=None
    ).delete()

    # Recently unsubscribed: anonymize data
    # but keep hash to prove existence
    subs = Subscriber.objects.filter(unsubscribed__lt=three_days_ago, email_hash="")
    for sub in subs:
        m = hashlib.sha256()
        # Kind of a salt
        m.update(str(sub.pk).encode("utf-8"))
        m.update(sub.get_email().lower().encode("utf-8"))
        sub.email_hash = m.hexdigest()
        sub.email = None
        sub.user = None
        sub.name = ""
        sub.save()


def send_onboarding_schedule(date: datetime.date):
    schedule = getattr(settings, "NEWSLETTER_ONBOARDING_SCHEDULE", [])
    for item in schedule:
        send_onboarding_schedule_item(date, item)


def send_onboarding_schedule_item(date: datetime.date, schedule_item):
    intent = mail_registry.get_intent(schedule_item["mail_intent"])
    if not intent:
        return

    subscribers = get_onboarding_subscribers(date, schedule_item)
    for subscriber in subscribers:
        subscriber.send_mail_intent(intent)


def get_onboarding_subscribers(date: datetime.date, schedule_item):
    date_gte, date_lt = schedule_item["date"](date)
    return Subscriber.objects.filter(
        newsletter__slug=schedule_item["newsletter"],
        subscribed__date__gte=date_gte,
        subscribed__date__lt=date_lt,
    )


def import_csv(csv_file, newsletter, reference="", email_confirmed=False):
    reader = csv.DictReader(csv_file)
    for row in reader:
        email = row["email"]
        if "name" in row:
            name = row.get("name", "")
        elif "first_name" in row and "last_name" in row:
            name = "{} {}".format(row["first_name"], row["last_name"])
        else:
            name = ""
        subscribe_email(
            newsletter,
            email,
            name=name,
            email_confirmed=email_confirmed,
            reference=reference,
            batch=True,
        )
