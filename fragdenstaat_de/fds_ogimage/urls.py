from django.urls import path
from django.utils.translation import pgettext_lazy

from .views import ProfileOGView


urlpatterns = [
    path(pgettext_lazy('url part', 'profile/<str:slug>/_og/'),
    ProfileOGView.as_view(), name='account-profile-og'),
]
