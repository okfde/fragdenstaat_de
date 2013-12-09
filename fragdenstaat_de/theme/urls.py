from django.conf.urls import patterns, url, include
from django.http import HttpResponseRedirect


urlpatterns = patterns('fragdenstaat_de.theme.views',
    (r'^presse/(?P<slug>[-\w]+)/$', 'show_press', {}, 'fds-show_press'),
    url(r'^nordrhein-westfalen/', lambda request: HttpResponseRedirect('/nrw/'),
        name="jurisdiction-nrw-redirect"),
    url(r'^rlp/', lambda request: HttpResponseRedirect('/rheinland-pfalz/'),
        name="jurisdiction-rlp-redirect"),
)

urlpatterns += patterns('',
    # Translators: URL part
    (r'^nachrichten/', include('foiidea.urls')),
)
