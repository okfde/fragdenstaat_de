from newsletter.models import Subscription

REFERENCE_PREFIX = 'newsletter-'


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
