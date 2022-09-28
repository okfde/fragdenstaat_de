from django.urls import path

from .views import ab_test

app_name = "fds_abtesting"

urlpatterns = [path("abtest/", ab_test, name="ab_test")]
