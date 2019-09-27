from django.urls import path

from .views import make_order

urlpatterns = [
    path('order/<slug:category>/', make_order, name='make_order'),
]
