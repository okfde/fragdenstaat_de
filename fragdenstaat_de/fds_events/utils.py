from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

import icalendar
from froide_legalaction.models import Instance
from froide_legalaction.utils import add_ical_events as add_legalaction_ical_events

from .models import Event


def make_event_calendar():
    cal = icalendar.Calendar()
    cal.add(
        "prodid",
        "-//{site_name} {detail} //{domain}//".format(
            site_name=settings.SITE_NAME,
            detail=_("FragDenStaat Events"),
            domain=settings.SITE_URL.split("/")[-1],
        ),
    )
    cal.add("version", "2.0")
    cal.add("method", "PUBLISH")

    events = Event.objects.get_upcoming()
    print(events)
    for event in events:
        ical_events = make_ical_event(event)
        cal.add_component(ical_events)

    instances = Instance.objects.get_last_three_months()
    for instance in instances:
        court_events = add_legalaction_ical_events(instance)
        cal.add_component(court_events)

    return cal


def make_ical_event(event: Event):
    uid = "event-%s-{pk}@{domain}".format(
        pk=event.pk, domain=settings.SITE_URL.split("/")[-1]
    )

    obj = icalendar.Event()
    obj.add("uid", uid % "fds-event")
    obj.add("dtstamp", timezone.now())
    obj.add("dtstart", event.start_date)
    obj.add("dtend", event.end_date)

    if event.location:
        obj.add("location", event.location)

    obj.add("summary", event.title)
    obj.add("description", event.description)

    return obj
