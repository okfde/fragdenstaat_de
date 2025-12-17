from django.urls import path, re_path
from django.utils.translation import pgettext_lazy

from .views import (
    DonationCompleteView,
    DonationFailedView,
    DonationView,
    DonorChangeView,
    DonorDonationActionView,
    DonorView,
    donor_login,
    donor_logout,
    get_legacy_redirect,
    make_order,
    send_donor_login_link,
)

app_name = "fds_donation"

urlpatterns = [
    path("order/<slug:category>/", make_order, name="make_order"),
    path(
        pgettext_lazy("url pattern", "donate/"), DonationView.as_view(), name="donate"
    ),
    path(
        pgettext_lazy("url pattern", "donate/complete/"),
        DonationCompleteView.as_view(),
        name="donate-complete",
    ),
    path(
        pgettext_lazy("url pattern", "donate/failed/"),
        DonationFailedView.as_view(),
        name="donate-failed",
    ),
    path(
        pgettext_lazy("url pattern", "your-donation/"),
        DonorView.as_view(),
        name="donor",
    ),
    path(
        pgettext_lazy("url pattern", "send-link/"),
        send_donor_login_link,
        name="donor-send-login-link",
    ),
    path(
        pgettext_lazy("url pattern", "logout/"),
        donor_logout,
        name="donor-logout",
    ),
    re_path(
        pgettext_lazy(
            "url pattern",
            r"^go/(?P<donor_id>\d+)/(?P<token>[^/]+)(?P<next_path>/.*)$",
        ),
        donor_login,
        name="donor-login",
    ),
    re_path(
        pgettext_lazy(
            "url pattern",
            r"^your-donation/(?P<token>[0-9a-z]{8}-[0-9a-z]{4}-"
            "[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12})/$",
        ),
        get_legacy_redirect("fds_donation:donor"),
        name="donor-legacy",
    ),
    path(
        pgettext_lazy("url pattern", "your-donation/change/"),
        DonorChangeView.as_view(),
        name="donor-change",
    ),
    re_path(
        pgettext_lazy(
            "url pattern",
            r"^your-donation/(?P<token>[0-9a-z]{8}-[0-9a-z]{4}-"
            r"[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12})/change/$",
        ),
        get_legacy_redirect("fds_donation:donor-change"),
        name="donor-legacy-change",
    ),
    path(
        pgettext_lazy("url pattern", "your-donation/donate/"),
        DonorDonationActionView.as_view(),
        name="donor-donate",
    ),
    re_path(
        pgettext_lazy(
            "url pattern",
            r"^your-donation/(?P<token>[0-9a-z]{8}-[0-9a-z]{4}-"
            r"[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12})/donate/$",
        ),
        get_legacy_redirect("fds_donation:donor-donate"),
        name="donor-legacy-donate",
    ),
]
