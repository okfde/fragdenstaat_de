from django.conf import settings

from froide.helper.email_sending import mail_registry

from .models import REFERENCE_PREFIX, Subscriber
from .utils import subscribe_to_default_newsletter, unsubscribe_queryset


def activate_newsletter_subscription(sender, **kwargs):
    # Subscribe previously setup subscriber objects
    unconfirmed_user_subscribers = Subscriber.objects.filter(
        user=sender, subscribed__isnull=True
    )
    for subscriber in unconfirmed_user_subscribers:
        subscriber.subscribe()

    confirmed_email_subscribers = Subscriber.objects.filter(
        email=sender.email.lower(), subscribed__isnull=False
    )
    for subscriber in confirmed_email_subscribers:
        subscriber.subscribe()


def user_email_changed(sender, old_email=None, **kwargs):
    # All subs with the new email
    subs = Subscriber.objects.filter(email=sender.email, user__isnull=True)
    for sub in subs:
        # Find existing user subs on that newsletter
        exists = Subscriber.objects.filter(
            user=sender, newsletter=sub.newsletter
        ).exists()
        if exists:
            # Delete email sub in favor of existing user sub
            sub.delete()
        else:
            # Change email sub to user sub
            sub.email = None
            sub.name = ""
            sub.user = sender
            sub.save()


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    old_subscribers = Subscriber.objects.filter(user=old_user)
    for sub in old_subscribers:
        new_qs = Subscriber.objects.filter(
            newsletter_id=sub.newsletter_id, user=new_user
        )
        if new_qs.exists():
            sub.delete()
        else:
            sub.user = new_user
            sub.save()


def cancel_user(sender, user=None, **kwargs):
    if user is None:
        return

    Subscriber.objects.filter(user=user, subscribed__isnull=True).delete()

    # Keep NL subscriptions with email subscription
    if user.email:
        subs = Subscriber.objects.filter(subscribed__isnull=False, user=user)
        for sub in subs:
            exists = Subscriber.objects.filter(
                newsletter_id=sub.newsletter_id, email=user.email
            ).exists()
            if not exists:
                sub.user = None
                sub.email = user.email
                sub.save(update_fields=["user", "email"])

    # Delete all other user subscriber connections
    Subscriber.objects.filter(
        user=user,
    ).delete()


def subscribe_follower(sender, **kwargs):
    if not sender.confirmed:
        return
    if not sender.context:
        return
    if not sender.context.get("newsletter"):
        return

    email = sender.email
    if not email:
        email = sender.user.email

    subscribe_to_default_newsletter(
        email,
        user=sender.user,
        email_confirmed=True,
        reference="follow_extra",
        keyword="{}:{}".format(sender._meta.label_lower, sender.content_object_id),
    )


def handle_unsubscribe(sender, email, reference, **kwargs):
    if not reference.startswith(REFERENCE_PREFIX):
        # not for us
        return
    try:
        sub_id = int(reference.split(REFERENCE_PREFIX, 1)[1])
    except ValueError:
        return
    try:
        subscriber = Subscriber.objects.all().select_related("user").get(id=sub_id)
    except Subscriber.DoesNotExist:
        return
    email = email.lower()
    if (subscriber.email and subscriber.email.lower() == email) or (
        subscriber.user and subscriber.user.email.lower() == email
    ):
        subscriber.unsubscribe(method="unsubscribe-mail")


def handle_bounce(sender, bounce, should_deactivate=False, **kwargs):
    if not should_deactivate:
        return
    if bounce.user:
        subscribers = Subscriber.objects.filter(user=bounce.user)
    else:
        subscribers = Subscriber.objects.filter(email=bounce.email)
    unsubscribe_queryset(subscribers, method="bounced")


def send_welcome_mail(sender, **kwargs):
    welcome = getattr(settings, "NEWSLETTER_WELCOME_MAILINTENT", None)
    if not welcome:
        return
    if not sender.subscribed:
        return
    for nl_slug, intent_id in welcome.items():
        if sender.newsletter.slug != nl_slug:
            continue
        intent = mail_registry.get_intent(intent_id)
        if not intent:
            return
        sender.send_mail_intent(intent)
