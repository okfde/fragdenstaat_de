from django.urls import path

from .views import add_postal_message, paperless_start

urlpatterns = [
    path(
        "<int:pk>/",
        paperless_start,
        name="paperless_index",
    ),
    path(
        "import/<slug:slug>/",
        add_postal_message,
        name="paperless_import",
    ),
]
