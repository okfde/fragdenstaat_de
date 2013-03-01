from django.conf.urls import patterns, url
from django.http import HttpResponseRedirect


urlpatterns = patterns('fragdenstaat_de.views',
    (r'^presse/(?P<slug>[-\w]+)/$', 'show_press', {}, 'fds-show_press'),
    url(r'^nordrhein-westfalen/', lambda request: HttpResponseRedirect('/nrw/'),
        name="jurisdiction-nrw-redirect")
)
