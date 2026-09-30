import logging
from functools import partial
from pathlib import Path

from django.conf import settings
from django.core.mail import mail_admins
from django.db import transaction
from django.utils import timezone

from froide.celery import app as celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="fragdenstaat_de.fds_mailing.send_mailing")
def send_mailing(mailing_id, sending_date):
    from .models import Mailing

    try:
        mailing = Mailing.objects.get(
            id=mailing_id,
            ready=True,
            submitted=True,
            sent=False,
            sending=False,
            sending_date=sending_date,
        )
    except Mailing.DoesNotExist:
        mail_admins("Mailing %d not sent!" % mailing_id, "")
        return
    mailing.finalize()

    continue_sending.delay(mailing_id)


@celery_app.task(name="fragdenstaat_de.fds_mailing.continue_sending")
def continue_sending(mailing_id):
    from .models import Mailing

    mailings = Mailing.objects.select_for_update().filter(
        id=mailing_id, ready=True, submitted=True, sent=False, sending=False
    )
    with transaction.atomic():
        mailing = mailings.first()
        if mailing is None:
            return

        mailing.continue_sending()

    missing_count = mailing.get_waiting_recipients().count()
    if missing_count == 0:
        mailing.sent = True
        mailing.sent_date = timezone.now()
        mailing.save()
    else:
        transaction.on_commit(partial(continue_sending.delay, mailing.id))


@celery_app.task(name="fragdenstaat_de.fds_mailing.process_pixel_log")
def process_pixel_log():
    from .pixel_log_parsing import PixelProcessor, get_pixel_log_generator

    pixel_log_path_str = settings.NEWSLETTER_PIXEL_LOG
    if not pixel_log_path_str:
        logger.warning("No pixel log path empty, skipping pixel log processing.")
        return
    pixel_log_path = Path(pixel_log_path_str)
    if not pixel_log_path.exists():
        logger.warning(
            "Pixel log path %s does not exist, skipping pixel log processing.",
            pixel_log_path,
        )
        return

    pixel_generator = get_pixel_log_generator(pixel_log_path)
    processor = PixelProcessor(pixel_generator)
    processor.run()
