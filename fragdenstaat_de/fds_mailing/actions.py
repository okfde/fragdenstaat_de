from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from flowcontrol.base import BaseAction, FlowDirective
from flowcontrol.registry import register_action

from fragdenstaat_de.fds_mailing.models import (
    DelayMailActionConfig,
    MailingMessage,
    SendMailActionConfig,
)


def filter_mailing_messages_to_object(obj, email):
    """Filter a queryset of MailingMessage to the given object."""
    qs = MailingMessage.objects.all()
    obj_key = obj.__class__.__name__.lower()
    fields = {field.name for field in MailingMessage._meta.get_fields()}
    if obj_key in fields:
        return qs.filter(**{obj_key: obj})

    return qs.filter(email=email)


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
class DelayMailAction(BaseAction):
    verbose_name = _("Delay if mail sent recently")
    description = _("Delays next action if an email was sent recently.")
    group = _("Mailing")
    model = DelayMailActionConfig

    def run(self, *, run, obj, config):
        if obj is None:
            raise ValueError("DelayMailAction requires an object to run on.")

        if config.delay_days == 0:
            return FlowDirective.CONTINUE

        email = get_email_from_object(obj)

        if config.max_delay_days > 0:
            key = f"_delay_mail_action_{config.id}"
            timestamp = run.state.get(key)
            if timestamp is None:
                run.state[key] = timezone.now().isoformat()
            else:
                timestamp = datetime.fromisoformat(timestamp)
                if timestamp + timedelta(days=config.max_delay_days) > timezone.now():
                    # Past max delay days reached, continue immediately
                    return FlowDirective.CONTINUE

        sent_after = timezone.now() - timedelta(days=config.delay_days)
        latest_message = (
            MailingMessage.objects.filter(email=email, sent__gte=sent_after)
            .order_by("-sent")
            .first()
        )
        if latest_message is None:
            return FlowDirective.CONTINUE

        new_sent_date = latest_message.sent + timedelta(days=config.delay_days)
        run.continue_after = new_sent_date
        return FlowDirective.SUSPEND_AND_REPEAT


@register_action
class SendMailAction(BaseAction):
    verbose_name = _("Send email")
    description = _("Send an email")
    group = _("Mailing")
    model = SendMailActionConfig
    raw_id_fields = ("email_template",)

    def run(self, *, run, obj, config):
        if obj is None:
            raise ValueError("SendMailAction requires an object to run on.")

        if not getattr(obj, "can_email", True):
            run.append_log("{}: Cannot send email to {}".format(config, obj))
            return

        email = get_email_from_object(obj)
        obj_key = obj.__class__.__name__.lower()

        if config.only_once:
            # Check if an email has already been sent to this contact with this template
            mailing_message_exists = (
                filter_mailing_messages_to_object(obj, email)
                .filter(mailing__email_template=config.email_template)
                .exists()
            )
            if mailing_message_exists:
                run.append_log("{}: Email already sent to {}".format(config, obj))
                return

        context = self.get_context().copy()
        context[obj_key] = obj
        config.email_template.send(
            email,
            context=context,
        )
