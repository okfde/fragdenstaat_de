from django.conf.urls import url
from django.urls import path, re_path

from .views import (
    NewsletterListView, NewsletterDetailView,
    newsletter_ajax_subscribe_request, newsletter_user_settings,
    SubscribeRequestView,
    NicerSubmissionArchiveDetailView,
    NicerSubmissionArchiveIndexView
)


urlpatterns = [
    path('user-settings/',
        newsletter_user_settings,
        name='newsletter_user_settings'
    ),
    path('subscribe-ajax/<slug:newsletter_slug>/',
        newsletter_ajax_subscribe_request,
        name='newsletter_ajax_subscribe_request'
    ),
    path(
        '<slug:newsletter_slug>/subscribe/',
        SubscribeRequestView.as_view(),
        name='newsletter_subscribe_request'
    ),
    path(
        '<slug:newsletter_slug>/subscription/<int:pk>/activate/<slug:slug>',
        SubscribeRequestView.as_view(),
        name='newsletter_subscribe_request'
    ),
    # legacy URLs
    path('', NewsletterListView.as_view(), name='newsletter_list'),
    path(
        '<slug:newsletter_slug>/',
        NewsletterDetailView.as_view(), name='newsletter_detail'
    ),

    re_path(
        r'^(?P<newsletter_slug>[\w-]+)/subscription/'
        r'(?P<email>[-_a-zA-Z0-9@\.\+~]+)/'
        r'(?P<action>(?:subscribe|update|unsubscribe))/'
        r'activate/(?P<activation_code>[\w-]+)/$',
        SubscribeRequestView.as_view(),
    ),
    url(r'^(?P<newsletter_slug>[\w-]+)/archiv/(?P<year>\d+)/(?P<month>\d+)/(?P<day>\d+)/(?P<pk>\d+)/$',
        NicerSubmissionArchiveDetailView.as_view(),
        name='newsletter_archive_detail'),
    re_path(r'^(?P<newsletter_slug>[\w-]+)/archiv/$',
        NicerSubmissionArchiveIndexView.as_view(), name='newsletter_archive'
    ),
]
