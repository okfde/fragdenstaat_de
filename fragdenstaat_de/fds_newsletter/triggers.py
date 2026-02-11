from django.utils.translation import gettext as _

from flowcontrol.registry import register_trigger

run_newsletter_subscribed_trigger = register_trigger(
    "newsletter_subscribed", label=_("Newsletter subscribed")
)

run_newsletter_unsubscribed_trigger = register_trigger(
    "newsletter_unsubscribed", label=_("Newsletter unsubscribed")
)


def newsletter_subscribed_trigger_listener(sender, batch=False, **kwargs):
    run_newsletter_subscribed_trigger(obj=sender, state={"batch": batch})


def newsletter_unsubscribed_trigger_listener(sender, **kwargs):
    run_newsletter_unsubscribed_trigger(obj=sender, state=kwargs)
