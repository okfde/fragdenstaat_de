from django.utils.translation import gettext_lazy as _

from flowcontrol.base import BaseAction
from flowcontrol.registry import register_action

from .models import SubscriberTagActionConfig, SubscribeToNewsletterActionConfig
from .utils import subscribe


@register_action
class SubscribeToNewsletterAction(BaseAction):
    verbose_name = _("Subscribe to newsletter")
    description = _(
        "Subscribes the current object's email address to a configured newsletter"
    )
    group = _("Mailing")
    model = SubscribeToNewsletterActionConfig

    def run(self, *, run, obj, config: SubscribeToNewsletterActionConfig):
        if obj is None:
            raise ValueError(
                "SubscribeToNewsletterAction requires an object to run on."
            )

        email = getattr(obj, "email", None)
        if not email:
            if hasattr(obj, "get_email"):
                email = obj.get_email()
        if not email:
            raise ValueError(
                "SubscribeToNewsletterAction requires an object with an 'email' attribute or a 'get_email' method."
            )

        subscribe(
            config.newsletter,
            email,
            email_confirmed=config.email_confirmed,
            reference=config.reference,
        )


@register_action
class ChangeSubscriberTag(BaseAction):
    verbose_name = _("Change tag on subscriber")
    description = _("Adds or removes the specified tag on the subscriber")
    group = _("Mailing")
    model = SubscriberTagActionConfig
    raw_id_fields = ("tag",)

    def run(self, *, run, obj, config: SubscriberTagActionConfig):
        if obj is None:
            raise ValueError("ChangeSubscriberTag requires an object to run on.")
        if config.remove:
            obj.tags.remove(config.tag)
        else:
            obj.tags.add(config.tag)
