from django import template
from django.conf import settings

from ..forms import NewsletterForm, NewslettersUserForm
from ..models import Newsletter
from ..utils import has_newsletter

register = template.Library()


@register.inclusion_tag("fds_newsletter/user_settings.html", takes_context=True)
def newsletter_settings(context):
    request = context["request"]
    user = request.user
    return {"newsletter_form": NewslettersUserForm(user)}


def _get_newsletter(newsletter_slug=None):
    try:
        return Newsletter.objects.get(
            slug=newsletter_slug or settings.DEFAULT_NEWSLETTER
        )
    except Newsletter.DoesNotExist:
        return None


def get_newsletter_context(context, next=None, newsletter=None, fallback=True):
    ctx = {"next": next, "fallback": fallback, "has_newsletter": False}

    if newsletter is None:
        ctx["has_newsletter"] = True
        return ctx

    ctx["newsletter"] = newsletter
    ctx["form"] = NewsletterForm(request=context["request"])
    ctx["has_newsletter"] = has_newsletter(context["request"].user, newsletter)
    user = context["request"].user
    ctx["user"] = user

    return ctx


@register.inclusion_tag(
    "fds_newsletter/plugins/smart_newsletter_form.html", takes_context=True
)
def newsletter_subscribe(context, next=None, newsletter_slug=None, fallback=True):
    newsletter = _get_newsletter(newsletter_slug)
    return get_newsletter_context(
        context, next=next, newsletter=newsletter, fallback=fallback
    )


@register.simple_tag(takes_context=True)
def newsletter_is_subscribed(context):
    newsletter = _get_newsletter()
    return has_newsletter(context["request"].user, newsletter)
