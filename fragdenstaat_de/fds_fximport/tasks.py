from froide.celery import app as celery_app

from . import helper


@celery_app.task(name="fragdenstaat_de.fds_fximport.import_case")
def import_case(message_id):
    from froide.foirequest.models import FoiMessage

    try:
        message = FoiMessage.objects.get(id=message_id)
    except FoiMessage.DoesNotExist:
        return

    helper.import_frontex_case(message)
