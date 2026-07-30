from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from flowcontrol.base import BaseAction, FlowDirective
from flowcontrol.registry import register_action

from .models import Donation, Donor, DonorTagActionConfig, RecentlyDonatedActionConfig


def get_email_from_object(obj):
    email = getattr(obj, "email", None)
    if not email:
        if hasattr(obj, "get_email"):
            email = obj.get_email()
    if not email:
        raise ValueError(
            "Requires an object with an 'email' attribute or a 'get_email' method."
        )
    return email


@register_action
class ChangeDonorTag(BaseAction):
    verbose_name = _("Change tag on donor")
    description = _("Adds or removes the specified tag on the donor")
    group = _("Donor")
    model = DonorTagActionConfig
    raw_id_fields = ("tag",)

    def run(self, *, run, obj, config: DonorTagActionConfig):
        if obj is None:
            raise ValueError("ChangeDonorTag requires an object to run on.")
        if config.remove:
            obj.tags.remove(config.tag)
        else:
            obj.tags.add(config.tag)


@register_action
class IfHasRecentlyDonated(BaseAction):
    verbose_name = _("If has recently donated")
    description = _("Checks if object has recently donated")
    group = _("Donor")
    model = RecentlyDonatedActionConfig
    has_children = True

    def run(self, *, run, obj, config: RecentlyDonatedActionConfig):
        if obj is None:
            raise ValueError("RecentlyDonated requires an object to run on.")
        donor = obj
        if not isinstance(obj, Donor):
            # Try to find donor via email
            email = get_email_from_object(obj)
            donor = Donor.objects.filter(
                email_confirmed__isnull=False, email=email
            ).first()
        if donor is not None:
            recently = timezone.now() - timedelta(days=config.since_days)
            if config.since_date:
                recently = config.since_date

            has_donated = Donation.objects.filter(
                donor=donor, completed=True, timestamp__gte=recently
            ).exists()
        else:
            # Could not find a donor
            has_donated = False

        if has_donated and not config.negate:
            return FlowDirective.ENTER
        elif not has_donated and config.negate:
            return FlowDirective.ENTER
        return FlowDirective.CONTINUE
