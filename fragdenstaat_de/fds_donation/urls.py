from django.urls import path
from django.utils.translation import pgettext_lazy

from .views import make_order, DonationView

urlpatterns = [
    path('order/<slug:category>/', make_order, name='make_order'),
    path(pgettext_lazy('url pattern', 'donate/'), DonationView.as_view(), name='donate'),
]
