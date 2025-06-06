from django.urls import path

from .views import (
    get_pdf_view,
    get_thumbnail_view,
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
    path("thumb/<int:paperless_document>/", get_thumbnail_view, name="paperless_thumb"),
    path("pdf/<int:paperless_document>/", get_pdf_view, name="paperless_pdf"),
]
