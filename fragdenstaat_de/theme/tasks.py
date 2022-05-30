from froide.celery import app as celery_app


@celery_app.task(name="fragdenstaat_de.theme.make_legal_backup")
def make_legal_backup(user_id):
    from froide.account.models import User

    from .legal_backup import make_legal_backup_for_user

    try:
        user = User.objects.get(
            id=user_id,
        )
    except User.DoesNotExist:
        return
    make_legal_backup_for_user(user)
