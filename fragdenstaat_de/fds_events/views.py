from django.http import HttpResponse
from django.views.generic import DetailView

import icalendar

from froide.helper.breadcrumbs import Breadcrumbs, BreadcrumbView

from .models import Event
from .utils import make_event_calendar, make_ical_event


def event_calendar_feed(request):
    cal = make_event_calendar()

    response = HttpResponse(cal.to_ical(), content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = "attachment; filename=events.ics"
    return response


class BaseEventDetailView(DetailView):
    model = Event

    def get_queryset(self):
        return super().get_queryset().filter(public=True)


class EventDetailView(BaseEventDetailView, BreadcrumbView):
    namespace = "fds_events"
    template_name = "fds_events/event_detail.html"
    context_object_name = "event"

    def get_breadcrumbs(self, context):
        items = []

        if "request" in context:
            request = context["request"]

            title = request.current_page.get_title()
            url = request.current_page.get_absolute_url()
            items.append((title, url))

        return Breadcrumbs(
            items=items + [(self.object.title, self.object.get_absolute_url())]
        )

    def optimize(self, queryset):
        return queryset.select_related("image")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.request.event = self.object

        if hasattr(self.request, "toolbar"):
            self.request.toolbar.set_object(self.object)

        context = self.get_context_data()
        return self.render_to_response(context)


class EventIcalDetailView(BaseEventDetailView):
    def get(self, request, *args, **kwargs):
        cal = icalendar.Calendar()
        event = make_ical_event(self.get_object())
        cal.add_component(event)

        response = HttpResponse(
            cal.to_ical(), content_type="text/calendar; charset=utf-8"
        )
        response["Content-Disposition"] = "attachment; filename=event.ics"

        return response
