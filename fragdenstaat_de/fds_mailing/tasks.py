from django.core.mail import mail_admins
from django.utils import timezone

from froide.celery import app as celery_app


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
    mailing.send()


@celery_app.task(name="fragdenstaat_de.fds_mailing.continue_sending")
def continue_sending(mailing_id):
    from .models import Mailing

    try:
        mailing = Mailing.objects.get(
            id=mailing_id, ready=True, submitted=True, sent=False, sending=False
        )
    except Mailing.DoesNotExist:
        return

    missing_recipients = mailing.recipients.all().filter(sent__isnull=True)
    context = mailing.get_email_context()

    try:
        for recipient in missing_recipients:
            recipient.send_message(context)
        mailing.sent = True
        mailing.sent_date = timezone.now()
    finally:
        mailing.sending = False
        mailing.save()
