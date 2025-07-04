from django.urls import path

from .views import (
    get_pdf_view,
    list_view,
    select_documents_view,
)

urlpatterns = [
    path("", list_view, name="paperless_list"),
    path(
        "import/<int:foirequest>/",
        select_documents_view,
        name="paperless_import",
    ),
    path("pdf/<int:paperless_document>/", get_pdf_view, name="paperless_pdf"),
]
