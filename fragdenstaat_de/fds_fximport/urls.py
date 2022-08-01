from django.urls import path

from .views import frontex_pad_import

urlpatterns = [
    path(
        "fronteximport/<slug:slug>/<int:message_id>/import/",
        frontex_pad_import,
        name="fragdenstaat-frontex_pad_import",
    ),
]
