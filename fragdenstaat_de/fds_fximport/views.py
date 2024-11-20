from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from froide.foirequest.models import FoiMessage
from froide.foirequest.views.request_actions import allow_write_foirequest

from .helper import is_frontex_msg
from .tasks import import_case


@require_POST
@allow_write_foirequest
def frontex_pad_import(request, foirequest, message_id):
    message = get_object_or_404(FoiMessage, request=foirequest, pk=message_id)
    is_message = is_frontex_msg(message)
    if not is_message:
        messages.add_message(
            request, messages.ERROR, _("This is not a message from frontex.")
        )
        return redirect(foirequest)

    import_case.delay(message.pk)
    messages.add_message(
        request,
        messages.SUCCESS,
        _("Import stated. You will receive an email once it finishes."),
    )

    return redirect(foirequest)
