from django.template import Library

from ..forms import SubscriptionCancelFeedbackForm

register = Library()


@register.simple_tag
def get_subscription_cancel_feedback_form():
    return SubscriptionCancelFeedbackForm()
