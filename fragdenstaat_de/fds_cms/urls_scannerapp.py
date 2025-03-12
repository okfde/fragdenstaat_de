from django.urls import re_path

from cms.urls import regexp

from .views import scannerapp_deeplink

app_name = "fds_cms"

urlpatterns = [
    re_path(regexp, scannerapp_deeplink, name="fds_cms-scannerapp_deeplink"),
]
