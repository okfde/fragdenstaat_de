from django.urls import path
from django.utils.translation import gettext_lazy as _

from .views import (
    SelectRequestView,
    add_postal_message,
    get_thumbnail_view,
    list_view,
)

urlpatterns = [
    path("", list_view, name="paperless_list"),
    path(
        "import/<slug:slug>/",
        add_postal_message,
        name="paperless_import",
    ),
    path(
        _("select-request/"),
        SelectRequestView.as_view(),
        name="paperless_select_request",
    ),
    path("thumb/<int:paperless_document>/", get_thumbnail_view, name="paperless_thumb"),
]
