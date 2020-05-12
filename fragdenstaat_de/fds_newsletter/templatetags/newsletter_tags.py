from django import template
from django.conf import settings
from django.forms.models import modelformset_factory

from newsletter.models import Newsletter, Subscription
from newsletter.forms import UserUpdateForm

from ..forms import NewsletterForm


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


def get_newsletter_context(context, next=None, newsletter_slug=None, fallback=True):
    ctx = {
        'next': next,
        'fallback': fallback
    }

    try:
        newsletter = Newsletter.objects.get(
            slug=newsletter_slug or settings.DEFAULT_NEWSLETTER
        )
    except Newsletter.DoesNotExist:
        ctx['has_newsletter'] = True
        return ctx

    ctx['newsletter'] = newsletter
    ctx['form'] = NewsletterForm(request=context['request'])
    user = context['request'].user

    if user.is_authenticated:
        try:
            instance = Subscription.objects.get(
                newsletter=newsletter, user=user
            )
            if instance.subscribed:
                ctx['has_newsletter'] = True
                return ctx
        except Subscription.DoesNotExist:
            pass

        ctx['user'] = user

    return ctx


@register.inclusion_tag('fds_newsletter/plugins/smart_newsletter_form.html',
                        takes_context=True)
def newsletter_subscribe(context, next=None, newsletter_slug=None, fallback=True):
    return get_newsletter_context(
        context, next=next, newsletter_slug=newsletter_slug, fallback=fallback
    )
