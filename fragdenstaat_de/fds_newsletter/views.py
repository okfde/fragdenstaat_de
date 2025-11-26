from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import Http404, get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from froide.helper.utils import get_redirect, is_ajax

from .forms import NewsletterForm, NewslettersUserForm, UnsubscribeFeedbackForm
from .models import Newsletter, Subscriber, UnsubscribeFeedback
from .utils import SubscriptionResult, subscribed_newsletters


@require_POST
@csrf_exempt
def newsletter_ajax_subscribe_request(request, newsletter_slug=None):
    if not is_ajax(request):
        raise Http404
    return newsletter_subscribe_request(request, newsletter_slug=newsletter_slug)


def newsletter_subscribe_request(request, newsletter_slug=None):
    newsletter = get_object_or_404(
        Newsletter, slug=newsletter_slug or settings.DEFAULT_NEWSLETTER
    )

    if request.method == "POST":
        form = NewsletterForm(
            data=request.POST,
            request=request,
        )
        if form.is_valid():
            result, subscriber = form.save(newsletter, request.user)

            user_subscriber = (
                request.user.is_authenticated and subscriber.user == request.user
            )

            if not user_subscriber and result == SubscriptionResult.ALREADY_SUBSCRIBED:
                subscriber.send_already_email()

            if is_ajax(request):
                # No-CSRF ajax request
                # are allowed to access current user
                if user_subscriber:
                    if result == SubscriptionResult.ALREADY_SUBSCRIBED:
                        return HttpResponse(
                            content=f"""<div class="alert alert-info" role="alert">
                        {_("You are already subscribed to our newsletter.")}
                        </div>""".encode("utf-8")
                        )
                    elif result == SubscriptionResult.SUBSCRIBED:
                        return HttpResponse(
                            content=f"""<div class="alert alert-primary" role="alert">
                        {_("You have been subscribed to our newsletter.")}
                        </div>""".encode("utf-8")
                        )

                return HttpResponse(
                    content=f"""<div class="alert alert-primary" role="alert">
                {_("You have received an email to confirm your subscription.")}
                </div>""".encode("utf-8")
                )

            if result == SubscriptionResult.CONFIRM:
                messages.add_message(
                    request,
                    messages.INFO,
                    _("You have received an email to confirm your subscription."),
                )

            return get_redirect(request, default="/")
        else:
            messages.add_message(
                request, messages.WARNING, _("Please correct the errors below.")
            )
    else:
        form = NewsletterForm(
            request=request,
            initial={
                "email": request.GET.get("email", ""),
                "reference": request.GET.get("reference", ""),
                "keyword": request.GET.get("keyword", ""),
                "next": request.GET.get("next", ""),
            },
        )

    if is_ajax(request):
        url = "{}?{}".format(
            reverse(
                "newsletter_subscribe_request",
                kwargs={"newsletter_slug": newsletter.slug},
            ),
            urlencode({"email": form.data.get("email", "")}),
        )
        return HttpResponse(url)
    return render(
        request,
        "fds_newsletter/subscribe.html",
        {"newsletter": newsletter, "form": form},
    )


def confirm_subscribe(request, newsletter_slug=None, pk=None, activation_code=None):
    newsletter = get_object_or_404(Newsletter, slug=newsletter_slug)
    subscriber = get_object_or_404(
        Subscriber,
        newsletter=newsletter,
        pk=pk,
        activation_code=activation_code,
    )
    if subscriber.unsubscribed:
        messages.add_message(
            request,
            messages.WARNING,
            _("You need to re-subscribe below to receive this newsletter."),
        )
        return redirect(newsletter.url or "/")

    subscriber.subscribe()
    messages.add_message(
        request, messages.INFO, _("You now receive the %s.") % newsletter.title
    )

    return redirect(newsletter.subscribed_url or "/")


def confirm_unsubscribe(request, newsletter_slug=None, pk=None, activation_code=None):
    newsletter = get_object_or_404(Newsletter, slug=newsletter_slug)
    subscriber = get_object_or_404(
        Subscriber, newsletter=newsletter, pk=pk, activation_code=activation_code
    )
    if request.method == "POST":
        subscriber.unsubscribe(
            method="unsubscribe-link", reference=request.GET.get("pk_campaign", "")
        )

        return redirect(
            reverse(
                "newsletter_unsubscribe_feedback",
                kwargs={"newsletter_slug": newsletter.slug},
            )
            + "?activation_code="
            + activation_code
        )
    return render(
        request,
        "fds_newsletter/unsubscribe.html",
        {"form_action": request.get_full_path()},
    )


def unsubscribe_feedback(request, newsletter_slug=None):
    newsletter = get_object_or_404(Newsletter, slug=newsletter_slug)

    if request.user.is_authenticated:
        subscriber = get_object_or_404(
            Subscriber, newsletter=newsletter, user=request.user
        )
    else:
        subscriber = get_object_or_404(
            Subscriber,
            newsletter=newsletter,
            activation_code=request.GET.get("activation_code"),
        )

    # make sure the user unsubscribed, and the unsubscription happened recently
    # and the survey has been filled out yet
    if (
        subscriber.unsubscribed is None
        or subscriber.unsubscribed > timezone.now() + timedelta(hours=1)
        or UnsubscribeFeedback.objects.filter(
            subscriber=subscriber, newsletter=newsletter
        ).exists()
    ):
        if request.user.is_authenticated:
            return redirect("account-settings")
        raise Http404

    if request.method == "POST":
        form = UnsubscribeFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.subscriber = subscriber
            feedback.newsletter = newsletter
            feedback.save()

            messages.add_message(
                request, messages.SUCCESS, _("Thank you for your feedback!")
            )

            return redirect(newsletter.unsubscribed_url or "/")
    else:
        form = UnsubscribeFeedbackForm()

    return render(
        request,
        "fds_newsletter/unsubscribe_feedback.html",
        {"form": form, "newsletter": newsletter},
    )


def legacy_unsubscribe(request, newsletter_slug=None, email=None, activation_code=None):
    newsletter = get_object_or_404(Newsletter, slug=newsletter_slug)
    subscriber = get_object_or_404(
        Subscriber, newsletter=newsletter, email=email, activation_code=activation_code
    )
    return redirect(subscriber.get_unsubscribe_url())


@require_POST
@login_required
def newsletter_user_settings(request):
    form = NewslettersUserForm(request.user, request.POST)
    if form.is_valid():
        previously_subscribed = set(subscribed_newsletters(request.user))
        chosen_newsletters = set(form.cleaned_data["newsletters"])
        form.save()

        unsubscribed = previously_subscribed - chosen_newsletters

        if len(unsubscribed) == 1:
            return redirect(
                reverse(
                    "newsletter_unsubscribe_feedback",
                    kwargs={"newsletter_slug": unsubscribed.pop().slug},
                )
            )
        elif len(unsubscribed) > 1:
            unsubscribed_slugs = [nl.slug for nl in unsubscribed]

            if settings.DEFAULT_NEWSLETTER in unsubscribed_slugs:
                return redirect(
                    reverse(
                        "newsletter_unsubscribe_feedback",
                        kwargs={"newsletter_slug": settings.DEFAULT_NEWSLETTER},
                    )
                )

        messages.add_message(
            request,
            messages.SUCCESS,
            _("Your newsletter subscriptions have been updated."),
        )
    else:
        messages.add_message(request, messages.ERROR, form.errors)

    return redirect("account-settings")
