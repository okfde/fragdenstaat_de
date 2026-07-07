from django.utils.translation import gettext_lazy as _

from flowcontrol.base import BaseAction, FlowDirective
from flowcontrol.registry import register_action

from .models import (
    HasTagActionConfig,
    InSegmentActionConfig,
    Subscriber,
    SubscriberTagActionConfig,
    SubscribeToNewsletterActionConfig,
)
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


@register_action
class IfInSegment(BaseAction):
    verbose_name = _("If is in segment")
    description = _("Check if an object is in a specific segment")
    group = _("Mailing")
    model = InSegmentActionConfig
    raw_id_fields = ("segment",)
    has_children = True

    def run(self, *, run, obj: Subscriber, config: InSegmentActionConfig):
        if obj is None:
            raise ValueError("IfInSegment requires an object to run on.")

        exist_in_segment = (
            config.segment.get_subscribers(newsletter=obj.newsletter)
            .filter(pk=obj.pk)
            .exists()
        )
        if exist_in_segment and not config.negate:
            return FlowDirective.ENTER
        elif not exist_in_segment and config.negate:
            return FlowDirective.ENTER
        return FlowDirective.CONTINUE


@register_action
class HasTagSegment(BaseAction):
    verbose_name = _("If has tag")
    description = _("Check if an object has a specific tag")
    group = _("Mailing")
    model = HasTagActionConfig
    raw_id_fields = ("tag",)
    has_children = True

    def run(self, *, run, obj: Subscriber, config: HasTagActionConfig):
        if obj is None:
            raise ValueError("HasTagSegment requires an object to run on.")

        has_tag = obj.tags.filter(pk=config.tag.pk).exists()
        if has_tag and not config.negate:
            return FlowDirective.ENTER
        elif not has_tag and config.negate:
            return FlowDirective.ENTER
        return FlowDirective.CONTINUE
