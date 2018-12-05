from newsletter.models import Subscription


def handle_bounce(bounce, should_deactivate=False, **kwargs):
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
