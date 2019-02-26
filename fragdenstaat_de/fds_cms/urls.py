from django.conf.urls import url

from .views import CMSPageSearch

urlpatterns = [
    url(r'^$', CMSPageSearch.as_view(), name='fds_cms-search'),
]
