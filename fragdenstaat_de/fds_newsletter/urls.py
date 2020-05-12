from django.urls import path, re_path

from newsletter.urls import urlpatterns as nl_urlpatterns

from .views import (
    newsletter_ajax_subscribe_request,
    newsletter_subscribe_request,
    newsletter_user_settings,
    NicerSubmissionArchiveDetailView,
    NicerSubmissionArchiveIndexView
)


urlpatterns = [
    path('user-settings/',
        newsletter_user_settings,
        name='newsletter_user_settings'
    ),
    path('subscribe-ajax/',
        newsletter_ajax_subscribe_request,
        name='newsletter_ajax_subscribe_request'
    ),
    path('subscribe/<slug:newsletter_slug>/',
        newsletter_subscribe_request,
        name='fds_newsletter_subscribe_request'
    ),
] + nl_urlpatterns + [
    # archive URLs
    re_path(r'^(?P<newsletter_slug>[\w-]+)/archiv/(?P<year>\d+)/(?P<month>\d+)/(?P<day>\d+)/(?P<pk>\d+)/$',
        NicerSubmissionArchiveDetailView.as_view(),
        name='newsletter_archive_detail'),
    re_path(r'^(?P<newsletter_slug>[\w-]+)/archiv/$',
        NicerSubmissionArchiveIndexView.as_view(), name='newsletter_archive'
    ),
]
