from django.conf.urls import patterns, include


urlpatterns = patterns('fragdenstaat_de.theme.views',
    (r'^presse/$', 'show_press', {}, 'fds-show_press'),
    (r'^presse/(?P<slug>[-\w]+)/$', 'show_press', {}, 'fds-show_press'),
)

urlpatterns += patterns('',
    # Translators: URL part
    (r'^nachrichten/', include('foiidea.urls')),
)
