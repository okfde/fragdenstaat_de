from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool


class FdsEventsToolbar(CMSToolbar):
    def populate(self):
        if hasattr(self.request, "event"):
            events_menu = self.toolbar.get_or_create_menu(
                "events-menu", pgettext_lazy("physical event", "Events")
            )

            event = self.request.event
            url = reverse("admin:fds_events_event_change", args=(event.pk,))
            events_menu.add_modal_item(_("Edit this event"), url=url)

            url = reverse("admin:fds_events_event_changelist")
            events_menu.add_modal_item(_("Events overview"), url=url)

            url = reverse("admin:fds_events_event_add")
            events_menu.add_modal_item(_("Create new event"), url=url)


toolbar_pool.register(FdsEventsToolbar)
