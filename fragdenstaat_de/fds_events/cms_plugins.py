import datetime

from django.utils.translation import pgettext_lazy

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from froide_legalaction.models import Lawsuit

from .models import Event


def sort_event(event: Event | Lawsuit) -> datetime.date:
    if isinstance(event.start_date, datetime.datetime):
        return event.start_date.date()
    return event.start_date


@plugin_pool.register_plugin
class NextEventsPlugin(CMSPluginBase):
    module = pgettext_lazy("physical event", "Events")
    name = pgettext_lazy("physical event", "Next events")
    render_template = "fds_events/event_list.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)

        # include the entirety of today
        events = Event.objects.get_upcoming()
        lawsuits = Lawsuit.upcoming.all()

        objects = sorted([*events, *lawsuits], key=sort_event, reverse=True)

        context.update({"events": objects})
        return context
