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
