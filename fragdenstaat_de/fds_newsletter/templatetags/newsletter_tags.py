from django import template
from django.forms.models import modelformset_factory

from newsletter.models import Newsletter, Subscription
from newsletter.forms import UserUpdateForm


register = template.Library()


@register.inclusion_tag('fds_newsletter/user_settings.html', takes_context=True)
def newsletter_settings(context):
    request = context['request']
    newsletters = Newsletter.on_site.filter(visible=True)
    user = request.user

    SubscriptionFormSet = modelformset_factory(
        Subscription, form=UserUpdateForm, extra=0
    )

    # Before rendering the formset, subscription objects should
    # already exist.
    for n in newsletters:
        Subscription.objects.get_or_create(
            newsletter=n, user=user
        )

    # Get all subscriptions for use in the formset
    qs = Subscription.objects.filter(
        newsletter__in=newsletters, user=user
    )
    formset = SubscriptionFormSet(queryset=qs)
    return {
        'formset': formset
    }


@register.inclusion_tag('fds_newsletter/subscribe.html', takes_context=True)
def newsletter_subscribe(context, newsletter_slug):
    return {
        'newsletter_slug': newsletter_slug
    }
