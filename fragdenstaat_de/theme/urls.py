from django.conf.urls import patterns, url
from django.contrib.flatpages import views


urlpatterns = patterns('',
    url(r'^hilfe/spenden/$', views.flatpage, {'url': '/hilfe/spenden/'}, name='help-donate'),
)
