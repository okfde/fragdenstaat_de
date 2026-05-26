from django.utils.translation import gettext as _

from flowcontrol.registry import register_trigger

run_recurrence_created_trigger = register_trigger(
    "recurrence_created", label=_("Recurrence created")
)
