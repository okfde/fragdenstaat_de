from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class FdsEventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fragdenstaat_de.fds_events"
    verbose_name = _("FragDenStaat Events")
