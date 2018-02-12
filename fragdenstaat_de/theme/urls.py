from django.conf.urls import include, url
from django.contrib.flatpages import views

from froide.urls import froide_urlpatterns, help_urlpatterns, jurisdiction_urls

from .views import index, gesetze_dashboard

urlpatterns = [
    url(r'^hilfe/spenden/$', views.flatpage, {'url': '/hilfe/spenden/'}, name='help-donate'),
    url(r'^kampagne/', include('froide_campaign.urls')),
    url(r'^klagen/', include('froide_legalaction.urls')),
    url(r'^gesetze/dashboard/$', gesetze_dashboard, name='fragdenstaat-gesetze_dashboard'),
    url(r'^$', index, name='index'),
]

urlpatterns += [
    url(r'^', include('filer.server.urls')),
]

urlpatterns += froide_urlpatterns + help_urlpatterns + jurisdiction_urls

urlpatterns += [
    url(r'^', include('cms.urls')),
]
