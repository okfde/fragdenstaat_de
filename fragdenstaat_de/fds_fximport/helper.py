import datetime
from typing import TYPE_CHECKING, Iterable, Iterator, Tuple

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from froide.account.services import AccountService
from froide.foirequest.models import FoiAttachment, FoiMessage, FoiRequest
from froide.foirequest.models.message import MessageKind
from froide.helper.storage import make_unique_filename
from froide.helper.text_utils import redact_subject

from .data import Direction, PadCase, PadMessage

if TYPE_CHECKING:
    from . import captcha
    from .askfx import FrontexPadClient

MARKER = "https://pad.frontex.europa.eu"
IMPORTED_TAG = "frontex_imported"


def get_content_type(data: bytes) -> str:
    import magic

    content_type = magic.from_buffer(data[:2048], mime=True)
    content_type = force_str(content_type)
    return content_type


def is_frontex_msg(message: FoiMessage) -> bool:
    text = message.plaintext
    # Make sure we short-circuit if the marker is not present
    return MARKER in text and has_valid_credentials(text)


def has_valid_credentials(text: str) -> bool:
    from .askfx import get_frontex_credentials_from_email

    credentials = get_frontex_credentials_from_email(text)
    return credentials is not None and credentials.valid_until >= datetime.date.today()


def add_msg_ids(
    case_id: str, messages: Iterable[PadMessage]
) -> Iterator[Tuple[str, PadMessage]]:
    msg_ids = {}
    for message in messages:
        message_id_base = f"{case_id}-{message.date.isoformat()}"
        idx = 0
        message_id = f"{message_id_base}-{idx}"
        while message_id in msg_ids:
            idx += 1
            message_id = f"{message_id_base}-{idx}"

        yield message_id, message


_captcha_net = None


def get_captcha_net() -> "captcha.Net":
    from . import captcha

    global _captcha_net
    if _captcha_net is None:
        if settings.FRONTEX_CAPTCHA_MODEL_PATH is None:
            raise Exception("You need to set the FRONTEX_CAPTCHA_MODEL_PATH")
        _captcha_net = captcha.load_net(settings.FRONTEX_CAPTCHA_MODEL_PATH)
    return _captcha_net


def import_messages_from_case(foirequest: FoiRequest, case: PadCase):
    user_replacements = foirequest.user.get_redactions()
    has_new_messages = False

    if case.messages:
        for message_id, pad_message in add_msg_ids(
            case.metadata.case_id, case.messages
        ):
            message_exists = (
                FoiMessage.objects.filter(request=foirequest)
                .exclude(email_message_id="")
                .filter(email_message_id=message_id)
                .filter(kind=MessageKind.IMPORT)
                .exists()
            )
            if message_exists:
                continue

            message = FoiMessage(
                request=foirequest,
                kind=MessageKind.IMPORT,
                timestamp=pad_message.date.replace(
                    tzinfo=timezone.get_current_timezone()
                ),
                plaintext=pad_message.message,
                email_message_id=message_id,
                subject=case.metadata.subject,
                subject_redacted=redact_subject(
                    case.metadata.subject, user_replacements
                ),
            )

            if pad_message.direction == Direction.IN:
                message.is_response = False
                message.sender_user = message.request.user
                message.recipient_public_body = foirequest.public_body
            else:
                message.is_response = True
                message.sender_public_body = foirequest.public_body

            message.plaintext_redacted = None
            message.plaintext_redacted = message.get_content()
            message.clear_render_cache()
            message.save()
            has_new_messages = True

        if has_new_messages:
            foirequest._messages = None
            foirequest.status = FoiRequest.STATUS.AWAITING_CLASSIFICATION
            foirequest.save()


def import_attachments_from_case(
    foirequest: FoiRequest, case: PadCase, client: "FrontexPadClient"
):
    names = set()
    account_service = AccountService(foirequest.user)

    last_imported_message = FoiMessage.objects.filter(
        request=foirequest, kind=MessageKind.IMPORT, is_response=True
    ).latest()

    for document in case.metadata.documents:
        name = f"imported_{document.name}"
        name = account_service.apply_name_redaction(name, str(_("NAME")))
        name = make_unique_filename(name, names)
        names.add(name)

        attachment_exists = FoiAttachment.objects.filter(
            belongs_to__request=foirequest,
            belongs_to__kind=MessageKind.IMPORT,
            name=name,
        ).exists()

        if attachment_exists:
            continue

        attachment_content = client.download_document(document)

        att = FoiAttachment.objects.create(
            belongs_to=last_imported_message,
            name=name,
            size=len(attachment_content),
            filetype=get_content_type(attachment_content),
            can_approve=True,
            approved=False,
        )

        if foirequest.not_publishable:
            att.can_approve = False

        att.file.save(content=ContentFile(attachment_content), name=name)
        att.save()


def import_frontex_case(source_message: FoiMessage):
    from .askfx import FrontexPadClient, get_frontex_credentials_from_email

    text = source_message.plaintext
    foirequest = source_message.request
    credentials = get_frontex_credentials_from_email(text)
    if credentials is None:
        return

    client = FrontexPadClient(credentials, captcha_net=get_captcha_net())
    case = client.load_pad_case()

    if case is None:
        return

    import_messages_from_case(foirequest, case)
    import_attachments_from_case(foirequest, case, client)

    source_message.tags.add(IMPORTED_TAG)
