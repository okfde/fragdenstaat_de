import json
from datetime import timedelta

from django.utils import timezone

from froide.celery import app as celery_app

from fragdenstaat_de.theme.notifications import send_notification

from .analytics import get_analytics
from .utils import cleanup_feedback, cleanup_subscribers, send_onboarding_schedule


@celery_app.task(name="fragdenstaat_de.fds_newsletter.cleanup_subscribers")
def cleanup_subscribers_task():
    cleanup_subscribers()


@celery_app.task(name="fragdenstaat_de.fds_newsletter.cleanup_feedback")
def cleanup_feedback_task():
    cleanup_feedback()


@celery_app.task(name="fragdenstaat_de.fds_newsletter.trigger_onboarding_schedule")
def trigger_onboarding_schedule():
    now = timezone.now()
    today = timezone.localdate(now)
    send_onboarding_schedule(today)


@celery_app.task(name="fragdenstaat_de.fds_newsletter.send_analytics")
def send_analytics():
    now = timezone.now()
    week = timedelta(days=7)
    start = now - week
    start_day = timezone.localdate(start)
    today = timezone.localdate(now)
    data = get_analytics(start_day, today)
    send_notification(
        "📊 Newsletter Analytics\n```{}```".format(json.dumps(data, indent=4))
    )


@celery_app.task(name="fragdenstaat_de.fds_newsletter.gather_subscriber_tags")
def gather_subscriber_tags():
    from .models import Subscriber

    qs = Subscriber.objects.get_subscribed()

    for subscriber in qs.iterator():
        subscriber.update_tags()
