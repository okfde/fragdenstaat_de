from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from froide.foirequest.auth import can_write_foirequest
from froide.foirequest.models import FoiRequest
from froide.helper.auth import require_crew
from froide.helper.utils import render_403

from .forms import PaperlessPostalReplyForm
from .paperless import (
    add_tag_to_documents,
    get_document_data,
    get_documents_by_correspondent,
)

User = get_user_model()


@require_crew
def list_view(request):
    users = User.objects.filter(
        groups__in=[settings.CREW_GROUP, settings.PAPERLESS_RECIPIENT_GROUP]
    ).order_by("first_name")
    return render(
        request,
        "fds_paperless/list_users.html",
        {"users": users},
    )


@require_crew
def select_documents_view(request, foirequest):
    foirequest = get_object_or_404(
        FoiRequest.objects.select_related("user"), pk=foirequest
    )

    if not can_write_foirequest(foirequest, request):
        return render_403(request)

    paperless_docs = get_documents_by_correspondent(foirequest.user.get_full_name())

    if request.method == "POST":
        form = PaperlessPostalReplyForm(
            data=request.POST,
            foirequest=foirequest,
            paperless_docs=paperless_docs,
        )

        if form.is_valid():
            message = form.save(request.user)
            FoiRequest.message_received.send(
                sender=foirequest, message=message, user=request.user
            )

            add_tag_to_documents(form.cleaned_data["paperless_ids"], foirequest)
            return redirect(message)
    else:
        form = PaperlessPostalReplyForm(
            foirequest=foirequest,
            paperless_docs=paperless_docs,
        )

    return render(
        request,
        "fds_paperless/select_documents.html",
        {"foirequest": foirequest, "documents": paperless_docs, "form": form},
    )


@require_crew
def get_pdf_view(request, paperless_document: int):
    content = get_document_data(paperless_document_id=paperless_document)
    return HttpResponse(content, content_type="application/pdf")
