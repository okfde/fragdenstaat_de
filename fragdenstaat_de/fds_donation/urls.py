from django.urls import path, re_path
from django.utils.translation import pgettext_lazy

from .views import (
    make_order, DonationView, DonationCompleteView,
    DonorUserView, DonorView,
    DonorChangeUserView, DonorChangeView,
)

app_name = 'fds_donation'

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

    path(pgettext_lazy('url pattern', 'your-donation/change/'),
         DonorChangeUserView.as_view(), name='donor-user-change'),
    re_path(pgettext_lazy('url pattern', r'^your-donation/(?P<token>[0-9a-z]{8}-[0-9a-z]{4}-'
        '[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12})/change/$'), DonorChangeView.as_view(),
        name='donor-change'),

]
