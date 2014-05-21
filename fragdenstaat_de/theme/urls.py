from django.conf.urls import patterns, include


urlpatterns = patterns('',
    # Translators: URL part
    (r'^nachrichten/', include('foiidea.urls')),
)
