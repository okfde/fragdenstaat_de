from newsletter.urls import urlpatterns as nl_urlpatterns

from django.conf.urls import url

from .views import (
    newsletter_ajax_subscribe_request, newsletter_user_settings,
    NicerSubmissionArchiveDetailView,
    NicerSubmissionArchiveIndexView
)


urlpatterns = [
    url(r'^user-settings/$',
        newsletter_user_settings,
        name='newsletter_user_settings'
    ),
    url(r'^subscribe-ajax/(?:(?P<newsletter_slug>[\w-]+)/)?$',
        newsletter_ajax_subscribe_request,
        name='newsletter_ajax_subscribe_request'
    ),
    url(r'^(?P<newsletter_slug>[\w-]+)/archive/(?P<year>\d+)/(?P<month>\d+)/(?P<day>\d+)/(?P<slug>[\w-]+)/$',
        NicerSubmissionArchiveDetailView.as_view(),
        name='newsletter_archive_detail'),
    url(r'^(?P<newsletter_slug>[\w-]+)/archiv/$',
        NicerSubmissionArchiveIndexView.as_view(), name='newsletter_archive'
    ),
] + nl_urlpatterns
