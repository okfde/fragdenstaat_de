from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import cache_control

from froide.foirequest.decorators import allow_write_foirequest
from froide.foirequest.models import FoiRequest
from froide.foirequest.views.list_requests import BaseListRequestView
from froide.helper.auth import require_staff
from froide.helper.utils import render_403

from .filters import SelectRequestFilterSet
from .forms import PaperlessPostalReplyForm
from .paperless import add_tag_to_documents, get_thumbnail, list_documents


@require_staff
def list_view(request):
    paperless_docs = list_documents()
    return render(
        request,
        "fds_paperless/list_documents.html",
        {
            "documents": paperless_docs,
        },
    )


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
            message = form.save(request.user)
            FoiRequest.message_received.send(
                sender=foirequest, message=message, user=request.user
            )

            add_tag_to_documents(form.cleaned_data["paperless_ids"])
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


@require_staff
@cache_control(max_age=86400)
def get_thumbnail_view(request, paperless_document: int):
    content_type, content = get_thumbnail(paperless_document_id=paperless_document)
    return HttpResponse(content, content_type=content_type)


class SelectRequestView(BaseListRequestView):
    template_name = "fds_paperless/select_request.html"
    search_url_name = "paperless_select_request"
    default_sort = "-last_message"
    select_related = ("public_body", "jurisdiction")

    filterset = SelectRequestFilterSet

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        documents = self.request.GET.getlist("paperless_ids")
        context["documents"] = documents

        return context
