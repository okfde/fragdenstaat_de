from django.urls import include, path
from django.utils.translation import pgettext_lazy

from .views import (
    FoiRequestOGView,
    GovPlanDetailOGView,
    GovPlanSectionDetailOGView,
    ProfileOGView,
)

govplan_patterns = (
    [
        path(
            pgettext_lazy("url part", "<slug:gov>/plan/<slug:plan>/_og/"),
            GovPlanDetailOGView.as_view(),
            name="plan_og",
        ),
        path(
            pgettext_lazy("url part", "<slug:gov>/<slug:section>/_og/"),
            GovPlanSectionDetailOGView.as_view(),
            name="section_og",
        ),
    ],
    "govplan_og",
)

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
    path("koalitionstracker/", include(govplan_patterns)),
]
