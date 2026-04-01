from django.urls import path

from .views import contact

app_name = "fds_easylang"

urlpatterns = [
    path("contact/", contact, name="contact"),
]
