from froide.celery import app as celery_app

from .utils import cleanup_subscribers


@celery_app.task(name='fragdenstaat_de.fds_newsletter.cleanup_subscribers')
def cleanup_subscribers_task():
    cleanup_subscribers()
