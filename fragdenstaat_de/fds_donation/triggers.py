from django.utils.translation import gettext as _

from flowcontrol.registry import register_trigger

run_recurrence_created_trigger = register_trigger(
    "recurrence_created", label=_("Recurrence created")
)


def recurrence_created_trigger_listener(sender, instance, **kwargs):
    if not kwargs["created"]:
        return
    if instance.cancel_date is not None:
        return
    if not instance.donor:
        return
    run_recurrence_created_trigger(obj=instance.donor)
