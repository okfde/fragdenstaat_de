from django.urls import path

from . import views

app_name = "fds_easylang"

urlpatterns = [
    path("", views.contact_form_view, name="contact_form"),
]
