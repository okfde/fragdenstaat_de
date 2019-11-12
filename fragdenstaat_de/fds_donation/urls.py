from django.urls import path, re_path
from django.utils.translation import pgettext_lazy

from .views import (
    make_order, DonationView, DonorUserView, DonorView,
    DonationCompleteView
)

urlpatterns = [
    path('order/<slug:category>/', make_order, name='make_order'),
    path(pgettext_lazy('url pattern', 'donate/'), DonationView.as_view(), name='donate'),
    path(pgettext_lazy('url pattern', 'donate/complete/'),
         DonationCompleteView.as_view(), name='donate-complete'),
    path(pgettext_lazy('url pattern', 'your-donation/'),
         DonorUserView.as_view(), name='donor-user'),
    re_path(pgettext_lazy('url pattern', r'^your-donation/(?P<token>[0-9a-z]{8}-[0-9a-z]{4}-'
        '[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12})/$'), DonorView.as_view(),
        name='donor'),
]
