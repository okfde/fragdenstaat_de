from django.core.mail import mail_admins

from froide.celery import app as celery_app


@celery_app.task(name='fragdenstaat_de.fds_newsletter.submit_submission')
def submit_submission(submission_id):
    from .models import Submission

    try:
        submission = Submission.objects.get(
            id=submission_id,
            prepared=True,
            sent=False,
            sending=False
        )
    except Submission.DoesNotExist:
        return
    submission.submit()


@celery_app.task(name='fragdenstaat_de.fds_newsletter.send_mailing')
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
    mailing.send()
