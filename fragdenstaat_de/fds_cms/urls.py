from django.urls import path

from .views import CMSPageSearch

app_name = "fds_cms"

urlpatterns = [
    path("", CMSPageSearch.as_view(), name="fds_cms-search"),
]
