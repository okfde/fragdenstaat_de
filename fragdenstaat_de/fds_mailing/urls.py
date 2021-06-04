from django.urls import path

from .views import MailingArchiveDetailView

urlpatterns = [
    path('<slug:newsletter_slug>/archiv/<int:year>/<int:month>/<int:day>/<int:pk>/',
        MailingArchiveDetailView.as_view(),
        name='newsletter_archive_detail'),
    # re_path(r'^(?P<newsletter_slug>[\w-]+)/archiv/$',
    #     NicerSubmissionArchiveIndexView.as_view(), name='newsletter_archive'
    # ),
]