from newsletter.models import Subscription

REFERENCE_PREFIX = 'newsletter-'


class SubscriptionResult:
    ALREADY_SUBSCRIBED = 0
    SUBSCRIBED = 1
    CONFIRM = 2


def handle_bounce(sender, bounce, should_deactivate=False, **kwargs):
    if not should_deactivate:
        return
    if bounce.user:
        Subscription.objects.filter(
            user=bounce.user
        ).update(subscribed=False)
    else:
        Subscription.objects.filter(
            email_field=bounce.email
        ).update(subscribed=False)


def handle_unsubscribe(sender, email, reference, **kwargs):
    if not reference.startswith(REFERENCE_PREFIX):
        # not for us
        return
    try:
        sub_id = int(reference.split(REFERENCE_PREFIX, 1)[1])
    except ValueError:
        return
    try:
        subscription = Subscription.objects.all().select_related('user').get(
            id=sub_id
        )
    except Subscription.DoesNotExist:
        return
    email = email.lower()
    if ((subscription.email_field and subscription.email_field.lower() == email) or
            (subscription.user and subscription.user.email.lower() == email)):
        subscription.subscribed = False
        subscription.save()


def subscribe(newsletter, email, user=None):
    if user and not user.is_authenticated:
        user = None
    if user and not user.is_active:
        # if user is not active, we have no confirmed address
        user = None

    email_confirmed = False
    if user and user.email.lower() == email.lower():
        email_confirmed = True

    if user and email_confirmed:
        if subscribe_user(newsletter, user):
            return SubscriptionResult.ALREADY_SUBSCRIBED
        return SubscriptionResult.SUBSCRIBED
    return subscribe_email(newsletter, email)


def subscribe_email(newsletter, email):
    subscription = Subscription.objects.get_or_create(
        email_field=email,
        newsletter=newsletter,
    )[0]

    if subscription.subscribed:
        return SubscriptionResult.ALREADY_SUBSCRIBED

    subscription.send_activation_email(action='subscribe')

    return SubscriptionResult.CONFIRM


def subscribe_user(newsletter, user):
    already_subscribed = False
    instance = Subscription.objects.get_or_create(
        newsletter=newsletter, user=user
    )[0]

    if instance.subscribed:
        already_subscribed = True
    else:
        instance.subscribed = True
        instance.save()
    return already_subscribed
