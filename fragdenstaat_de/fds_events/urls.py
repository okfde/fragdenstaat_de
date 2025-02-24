from django.urls import path

from .views import EventDetailView, EventIcalDetailView, event_calendar_feed

app_name = "fds_events"

urlpatterns = [
    path("calendar/ical/", event_calendar_feed, name="calendar-feed"),
    path("<slug:slug>/", EventDetailView.as_view(), name="event-detail"),
    path(
        "calendar/<slug:slug>/",
        EventIcalDetailView.as_view(),
        name="calendar-event-detail",
    ),
]
