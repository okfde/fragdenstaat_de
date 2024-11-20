import logging

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from froide.celery import app as celery_app
from froide.foirequest.models import FoiMessage
from froide.foirequest.models.message import MessageKind
from froide.foirequest.utils import send_request_user_email
from froide.helper.email_sending import mail_registry

from . import helper

logger = logging.getLogger(__name__)

fximport_success_mail = mail_registry.register(
    "fds_fximport/emails/success",
    ("action_url", "foirequest", "message", "user"),
)

fximport_failed_mail = mail_registry.register(
    "fds_fximport/emails/failed",
    ("action_url", "foirequest", "message", "user"),
)


@celery_app.task(name="fragdenstaat_de.fds_fximport.import_case")
def import_case(message_id):
    with transaction.atomic():
        try:
            message = FoiMessage.objects.get(id=message_id)
        except FoiMessage.DoesNotExist:
            return
        try:
            helper.import_frontex_case(message)
            newest_fx_message = (
                FoiMessage.objects.filter(request=message.request)
                .filter(kind=MessageKind.IMPORT)
                .last()
            )

            send_request_user_email(
                fximport_success_mail,
                message.request,
                subject=_("New Message imported"),
                context={
                    "message": message,
                    "foirequest": message.request,
                    "user": message.request.user,
                    "action_url": message.request.user.get_autologin_url(
                        newest_fx_message.get_absolute_short_url()
                    ),
                },
            )

        except Exception:
            logger.exception("Frontex import failed")
            send_request_user_email(
                fximport_failed_mail,
                message.request,
                subject=_("Message import failed"),
                context={
                    "message": message,
                    "foirequest": message.request,
                    "user": message.request.user,
                    "action_url": message.request.user.get_autologin_url(
                        message.get_absolute_short_url()
                    ),
                },
            )
