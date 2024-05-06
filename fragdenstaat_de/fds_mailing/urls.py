from django.urls import path

from .models import Mailing
from .views import MailingArchiveDetailView

urlpatterns = [
    path(
        "<slug:newsletter_slug>/archiv/<int:year>/<int:month>/<int:day>/<int:pk>/",
        MailingArchiveDetailView.as_view(model=Mailing),
        name="newsletter_archive_detail",
    ),
]
