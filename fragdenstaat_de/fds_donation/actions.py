from django.utils.translation import gettext_lazy as _

from flowcontrol.base import BaseAction
from flowcontrol.registry import register_action

from .models import DonorTagActionConfig


@register_action
class ChangeDonorTag(BaseAction):
    verbose_name = _("Add or removes a tag on the donor")
    description = _("Adds or removes the specified tag on the donor")
    group = _("Donor")
    model = DonorTagActionConfig

    def run(self, *, run, obj, config: DonorTagActionConfig):
        if obj is None:
            raise ValueError("ChangeDonorTag requires an object to run on.")
        if config.remove:
            obj.tags.remove(config.tag)
        else:
            obj.tags.add(config.tag)
