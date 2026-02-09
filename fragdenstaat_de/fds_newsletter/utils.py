import csv
import datetime
import hashlib
import string
from datetime import timedelta
from enum import Enum
from typing import List, Optional, Tuple

from django.conf import settings
from django.db import connection
from django.db.models import Q
from django.db.models.functions import Collate
from django.utils import timezone

from froide.helper.email_sending import mail_registry

from .models import (
    Newsletter,
    Segment,
    Subscriber,
    SubscriberTag,
    TaggedSubscriber,
    UnsubscribeFeedback,
)


class SubscriptionResult(Enum):
    ALREADY_SUBSCRIBED = 0
    ALREADY_SUBSCRIBED_EMAIL = 0
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
    tags=None,
) -> SubscriptionReturn:
    if user and not user.is_authenticated:
        user = None
    if user and not user.is_active:
        # if user is not active, we have no confirmed address
        user = None

    if user and user.email.lower() == email.lower():
        email_confirmed = True

    if user and email_confirmed:
        return subscribe_user(
            newsletter, user, reference=reference, keyword=keyword, tags=tags
        )
    return subscribe_email(
        newsletter,
        email,
        email_confirmed=email_confirmed,
        name=name,
        reference=reference,
        keyword=keyword,
        tags=tags,
    )


def subscribe_email(
    newsletter,
    email,
    email_confirmed=False,
    name="",
    reference="",
    keyword="",
    tags=None,
    batch=False,
) -> SubscriptionReturn:
    try:
        subscriber = (
            Subscriber.objects.annotate(
                user_email_deterministic=Collate("user__email", "und-x-icu"),
            )
            .filter(Q(email=email.lower()) | Q(user_email_deterministic=email))
            .get(newsletter=newsletter)
        )
    except Subscriber.DoesNotExist:
        subscriber, _created = Subscriber.objects.get_or_create(
            email=email.lower(),
            newsletter=newsletter,
            defaults={"name": name, "reference": reference, "keyword": keyword},
        )

    if tags:
        subscriber.tags.add(*tags)

    if subscriber.subscribed:
        if not batch:
            subscriber.send_already_email()
        return (SubscriptionResult.ALREADY_SUBSCRIBED_EMAIL, subscriber)
    if not email_confirmed:
        subscriber.send_activation_email(batch=batch)
        return (SubscriptionResult.CONFIRM, subscriber)

    subscriber = subscriber.subscribe(reference=reference, keyword=keyword, batch=batch)
    return (SubscriptionResult.SUBSCRIBED, subscriber)


def subscribe_user(
    newsletter, user, reference="", keyword="", tags=None
) -> SubscriptionReturn:
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
    if tags:
        subscriber.tags.add(*tags)

    if subscriber.subscribed:
        return (SubscriptionResult.ALREADY_SUBSCRIBED, subscriber)

    subscriber = subscriber.subscribe(reference=reference, keyword=keyword)
    return (SubscriptionResult.SUBSCRIBED, subscriber)


def has_newsletter(user, newsletter=None, newsletter_slug=None) -> bool:
    if not user.is_authenticated:
        return None
    if not newsletter:
        try:
            newsletter = Newsletter.objects.get(
                slug=newsletter_slug or settings.DEFAULT_NEWSLETTER
            )
        except Newsletter.DoesNotExist:
            return None

    return Subscriber.objects.filter(
        newsletter=newsletter, user=user, subscribed__isnull=False
    ).exists()


def subscribed_newsletters(user) -> List[Newsletter]:
    # .values_list would only result in a pk-list
    return [
        s.newsletter
        for s in Subscriber.objects.filter(user=user, subscribed__isnull=False)
    ]


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


def cleanup_feedback():
    now = timezone.now()
    hour_ago = now - timedelta(hours=1)
    UnsubscribeFeedback.objects.filter(created__lt=hour_ago).update(subscriber=None)


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


def import_csv(csv_file, newsletter, reference="", email_confirmed=False, tags=None):
    if tags is None:
        tags = set()
    else:
        tags = set(tags)
    reader = csv.DictReader(csv_file)
    for row in reader:
        email = row["email"]
        if "name" in row:
            name = row.get("name", "")
        elif "first_name" in row and "last_name" in row:
            name = "{} {}".format(row["first_name"], row["last_name"])
        else:
            name = ""
        row_tags = {t.strip() for t in row.get("tags", "").split(",") if t.strip()}
        row_tags |= tags
        subscribe_email(
            newsletter,
            email,
            name=name,
            email_confirmed=email_confirmed,
            reference=reference,
            tags=row_tags,
            batch=True,
        )


def get_subscribers(newsletter: Newsletter, segments: Optional[list[Segment]] = None):
    if not newsletter:
        return Subscriber.objects.none()
    qs = Subscriber.objects.filter(newsletter=newsletter, subscribed__isnull=False)

    if segments:
        first_segment = segments[0]
        out_qs = first_segment.filter_subscribers(qs)
        out_qs = out_qs.union(*[seg.filter_subscribers(qs) for seg in segments[1:]])
        qs = out_qs
    return qs


def generate_random_split(
    name: str, newsletter: Newsletter, segments: list[Segment], groups: list[int]
) -> list[Segment]:
    subscribers = get_subscribers(newsletter, segments)

    count = subscribers.count()
    group_sizes = [round(count * (g / 100.0)) for g in groups]
    group_total = sum(group_sizes)

    # Use a PostgreSQL CTE to select random subscribers
    # This is a workaround for Django not supporting random ordering in across unions
    subscriber_query = str(subscribers.values_list("id", flat=True).query)
    with connection.cursor() as cursor:
        cursor.execute(
            "WITH selection AS ({query}) SELECT id FROM selection ORDER BY RANDOM() LIMIT {limit}".format(
                query=subscriber_query, limit=group_total
            )
        )
        sub_ids = [row[0] for row in cursor.fetchall()]

    group_tags = []
    for i, group in enumerate(groups, start=0):
        group_letter = string.ascii_uppercase[i]
        tag_name = f"random:{name}:{group}%:{group_letter}"
        tag, _created = SubscriberTag.objects.get_or_create(
            name=tag_name,
        )
        group_tags.append(tag)

    start = 0
    for size, group_tag in zip(group_sizes, group_tags, strict=True):
        end = start + size
        TaggedSubscriber.objects.bulk_create(
            [
                TaggedSubscriber(
                    content_object_id=sub_id,
                    tag=group_tag,
                )
                for sub_id in sub_ids[start:end]
            ]
        )
        start = end

    target_segments = []
    for i, group_tag in enumerate(group_tags):
        group_letter = string.ascii_uppercase[i]
        segment = Segment.add_root(
            name=f"Group {group_letter} ({groups[i]}%) {name}",
            description=f"""Selects {groups[i]}% of the subscribers
                of newsletter {newsletter.title} and
                with segments {segments}""",
        )
        segment.tags.add(group_tag)
        target_segments.append(segment)
    return target_segments
