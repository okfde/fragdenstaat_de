from django.shortcuts import get_object_or_404, redirect, render

from froide.foirequest.auth import can_write_foirequest
from froide.foirequest.decorators import allow_write_foirequest
from froide.foirequest.models import FoiRequest
from froide.helper.utils import render_403

from .forms import PaperlessPostalReplyForm
from .paperless import list_documents


def paperless_start(request, pk):
    foirequest = get_object_or_404(FoiRequest, pk=pk)
    if not can_write_foirequest(foirequest, request):
        return render_403(request)
    return redirect("paperless_import", slug=foirequest.slug)


@allow_write_foirequest
def add_postal_message(request, foirequest):
    if not request.user.is_staff or not request.user.has_perm(
        "foirequest.change_foimessage"
    ):
        return render_403(request)

    paperless_docs = list_documents()
    if request.method == "POST":
        form = PaperlessPostalReplyForm(
            request.POST, foirequest=foirequest, paperless_docs=paperless_docs
        )
        if form.is_valid():
            message = form.save()
            FoiRequest.message_received.send(
                sender=foirequest, message=message, user=request.user
            )
            return redirect(message)
    else:
        form = PaperlessPostalReplyForm(
            foirequest=foirequest, paperless_docs=paperless_docs
        )

    return render(
        request,
        "fds_paperless/add_postal_message.html",
        {
            "object": foirequest,
            "form": form,
        },
    )
