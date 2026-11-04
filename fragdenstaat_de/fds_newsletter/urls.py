from django.urls import path
from django.utils.translation import gettext_lazy as _

from .views import (
    confirm_subscribe,
    confirm_unsubscribe,
    newsletter_ajax_subscribe_request,
    newsletter_subscribe_request,
    newsletter_user_settings,
    undo_unsubscribe,
    unsegment,
    unsubscribe_feedback,
    unsubscribed,
)

urlpatterns = [
    path("user-settings/", newsletter_user_settings, name="newsletter_user_settings"),
    path(
        "subscribe-ajax/",
        newsletter_ajax_subscribe_request,
        name="newsletter_ajax_subscribe_request",
    ),
    path(
        "<slug:newsletter_slug>/subscribe-ajax/",
        newsletter_ajax_subscribe_request,
        name="newsletter_ajax_subscribe_request",
    ),
    path(
        "subscribe/", newsletter_subscribe_request, name="newsletter_subscribe_request"
    ),
    path(
        "<slug:newsletter_slug>/subscribe/",
        newsletter_subscribe_request,
        name="newsletter_subscribe_request",
    ),
    path(
        "<slug:newsletter_slug>/subscription/<int:pk>/subscribe/<slug:activation_code>/",
        confirm_subscribe,
        name="newsletter_confirm_subscribe",
    ),
    path(
        "<slug:newsletter_slug>/subscription/<int:pk>/unsubscribe/<slug:activation_code>/",
        confirm_unsubscribe,
        name="newsletter_confirm_unsubscribe",
    ),
    path(
        "<slug:newsletter_slug>/subscription/undo-unsubscribe/",
        undo_unsubscribe,
        name="newsletter_undo_unsubscribe",
    ),
    path(
        "<slug:newsletter_slug>/subscription/<int:pk>/unsegment/<slug:activation_code>/<int:segment_id>/",
        unsegment,
        name="newsletter_unsegment",
    ),
    path(
        "<slug:newsletter_slug>/unsubscribed/",
        unsubscribed,
        name="newsletter_unsubscribed",
    ),
    path(
        _("<slug:newsletter_slug>/feedback/"),
        unsubscribe_feedback,
        name="newsletter_unsubscribe_feedback",
    ),
    # re_path(
    #     r'^(?P<newsletter_slug>[\w-]+)/subscription/'
    #     r'(?P<email>[-_a-zA-Z0-9@\.\+~]+)/'
    #     r'(?P<action>(?:subscribe|update|unsubscribe))/'
    #     r'activate/(?P<activation_code>[\w-]+)/$',
    #     SubscribeRequestView.as_view(),
    # )
]
