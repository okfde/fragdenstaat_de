from django.urls import path
from django.utils.translation import pgettext_lazy

from .views import ProfileOGView, FoiRequestOGView


urlpatterns = [
    path(
        pgettext_lazy("url part", "profile/<str:slug>/_og/"),
        ProfileOGView.as_view(),
        name="account-profile-og",
    ),
    path(
        pgettext_lazy("url part", "request/<str:slug>/_og/"),
        FoiRequestOGView.as_view(),
        name="foirequest-show-og",
    ),
]
