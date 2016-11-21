from django.conf.urls import include, url
from django.contrib.flatpages import views

from .views import index

urlpatterns = [
    url(r'^hilfe/spenden/$', views.flatpage, {'url': '/hilfe/spenden/'}, name='help-donate'),
    url(r'^kampagne/', include('froide_campaign.urls')),
    url(r'^verklagen/', include('froide_legalaction.urls')),
    url(r'^$', index, name='index'),
]
