from django.conf.urls import url

from .views import CMSPageSearch


app_name = "fds_cms"

urlpatterns = [
    url(r"^$", CMSPageSearch.as_view(), name="fds_cms-search"),
]
