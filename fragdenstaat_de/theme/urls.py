from django.conf.urls import include, url
from django.contrib.flatpages import views

from .views import index, gesetze_dashboard

urlpatterns = [
    url(r'^hilfe/spenden/$', views.flatpage, {'url': '/hilfe/spenden/'}, name='help-donate'),
    url(r'^kampagne/', include('froide_campaign.urls')),
    url(r'^klagen/', include('froide_legalaction.urls')),
    url(r'^gesetze/dashboard/$', gesetze_dashboard, name='fragdenstaat-gesetze_dashboard'),
    url(r'^$', index, name='index'),
]
