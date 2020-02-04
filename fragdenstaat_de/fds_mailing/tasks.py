from django.core.mail import mail_admins

from froide.celery import app as celery_app


@celery_app.task(name='fragdenstaat_de.fds_mailing.send_mailing')
def send_mailing(mailing_id, sending_date):
    from .models import Mailing

    try:
        mailing = Mailing.objects.get(
            id=mailing_id,
            ready=True,
            submitted=True,
            sent=False,
            sending=False,
            sending_date=sending_date
        )
    except Mailing.DoesNotExist:
        mail_admins(
            'Mailing %d not sent!' % mailing_id, ''
        )
        return
    mailing.finalize()
    mailing.send()
