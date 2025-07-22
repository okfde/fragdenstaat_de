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

        email = getattr(obj, "email", None)
        if not email:
            if hasattr(obj, "get_email"):
                email = obj.get_email()
        if not email:
            raise ValueError(
                "DelayMailAction requires an object with an 'email' attribute or a 'get_email' method."
            )

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

        email = getattr(obj, "email", None)
        if not email:
            if hasattr(obj, "get_email"):
                email = obj.get_email()
        if not email:
            raise ValueError(
                "SendMailAction requires an object with an 'email' attribute or a 'get_email' method."
            )

        context = run.context.copy()
        obj_key = obj.__class__.__name__.lower()
        context[obj_key] = obj
        config.email_template.send(
            email,
            context=context,
            subject=config.subject,
        )
