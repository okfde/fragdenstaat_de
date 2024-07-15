from django.urls import re_path

from cms.urls import regexp

from .views import cms_plain_api

app_name = "fds_cms"

urlpatterns = [
    re_path(regexp, cms_plain_api, name="fds_cms-plainapi"),
    re_path("", lambda r: cms_plain_api(r, ""), name="fds_cms-plainapi"),
]
