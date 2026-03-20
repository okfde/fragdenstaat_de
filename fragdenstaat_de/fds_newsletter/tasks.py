from froide.celery import app as celery_app

from .utils import cleanup_feedback, cleanup_subscribers


@celery_app.task(name="fragdenstaat_de.fds_newsletter.cleanup_subscribers")
def cleanup_subscribers_task():
    cleanup_subscribers()


@celery_app.task(name="fragdenstaat_de.fds_newsletter.cleanup_feedback")
def cleanup_feedback_task():
    cleanup_feedback()


@celery_app.task(name="fragdenstaat_de.fds_newsletter.gather_subscriber_tags")
def gather_subscriber_tags():
    from .models import Subscriber

    qs = Subscriber.objects.get_subscribed()

    for subscriber in qs.iterator():
        subscriber.update_tags()


@celery_app.task(name="fragdenstaat_de.fds_newsletter.run_subscriber_import")
def run_subscriber_import(subscriber_import_id):
    from .models import SubscriberImport

    try:
        subscriber_import = SubscriberImport.objects.get(
            completed=None, id=subscriber_import_id
        )
    except SubscriberImport.DoesNotExist:
        return

    subscriber_import.run_import()
