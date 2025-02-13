from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import cache_control

from froide.foirequest.decorators import allow_write_foirequest
from froide.foirequest.models import FoiRequest
from froide.foirequest.views.list_requests import BaseListRequestView
from froide.helper.auth import is_crew, require_crew
from froide.helper.utils import render_403

from .filters import SelectRequestFilterSet
from .forms import PaperlessPostalReplyForm
from .paperless import (
    add_tag_to_documents,
    get_documents,
    get_thumbnail,
    list_documents,
)


@require_crew
def list_view(request):
    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        page = 1
    paperless_docs = list_documents(page=page)
    return render(
        request,
        "fds_paperless/list_documents.html",
        {
            "documents": paperless_docs,
            "page": page,
            "next_page": page + 1,
            "prev_page": page - 1,
        },
    )


@allow_write_foirequest
def add_postal_message(request, foirequest):
    if not is_crew(request.user) or not request.user.has_perm(
        "foirequest.change_foimessage"
    ):
        return render_403(request)

    context = {"object": foirequest}

    selected_documents = request.GET.getlist("paperless_ids")
    paperless_docs = get_documents(selected_documents)
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
            foirequest=foirequest,
            paperless_docs=paperless_docs,
            initial={"paperless_ids": selected_documents},
        )
        context["documents"] = filter(
            lambda doc: str(doc["id"]) in selected_documents, paperless_docs
        )

    context["form"] = form

    return render(
        request,
        "fds_paperless/add_postal_message.html",
        context,
    )


@require_crew
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
