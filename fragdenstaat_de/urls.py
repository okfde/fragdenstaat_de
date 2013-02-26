from django.conf.urls.defaults import patterns


urlpatterns = patterns('fragdenstaat_de.views',
    (r'^presse/(?P<slug>[-\w]+)/$', 'show_press', {}, 'fds-show_press'),
)
