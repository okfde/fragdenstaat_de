from django import template
from django.conf import settings

from ..models import Newsletter, Subscriber
from ..forms import NewslettersUserForm, NewsletterForm


register = template.Library()


@register.inclusion_tag('fds_newsletter/user_settings.html', takes_context=True)
def newsletter_settings(context):
    request = context['request']
    user = request.user
    return {
        'form': NewslettersUserForm(user)
    }


def _get_newsletter(newsletter_slug=None):
    try:
        return Newsletter.objects.get(
            slug=newsletter_slug or settings.DEFAULT_NEWSLETTER
        )
    except Newsletter.DoesNotExist:
        return None


def _has_newsletter(context, newsletter):
    user = context['request'].user
    if user.is_authenticated:
        try:
            instance = Subscriber.objects.get(
                newsletter=newsletter, user=user
            )
            if instance.subscribed:
                return True
        except Subscriber.DoesNotExist:
            pass
    return False


def get_newsletter_context(context, next=None, newsletter_slug=None, fallback=True):
    ctx = {
        'next': next,
        'fallback': fallback,
        'has_newsletter': False
    }

    newsletter = _get_newsletter(newsletter_slug)
    if newsletter is None:
        ctx['has_newsletter'] = True
        return ctx

    ctx['newsletter'] = newsletter
    ctx['form'] = NewsletterForm(request=context['request'])
    ctx['has_newsletter'] = _has_newsletter(context, newsletter)
    user = context['request'].user
    ctx['user'] = user

    return ctx


@register.inclusion_tag('fds_newsletter/plugins/smart_newsletter_form.html',
                        takes_context=True)
def newsletter_subscribe(context, next=None, newsletter_slug=None, fallback=True):
    return get_newsletter_context(
        context, next=next, newsletter_slug=newsletter_slug, fallback=fallback
    )


@register.simple_tag(takes_context=True)
def newsletter_is_subscribed(context):
    newsletter = _get_newsletter()
    return _has_newsletter(context, newsletter)
