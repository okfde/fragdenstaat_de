from urllib.parse import urlencode

from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, Http404, render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from froide.helper.utils import get_redirect

from .models import Newsletter, Subscriber
from .forms import NewsletterForm, NewslettersUserForm
from .utils import SubscriptionResult


@require_POST
@csrf_exempt
def newsletter_ajax_subscribe_request(request, newsletter_slug=None):
    if not request.is_ajax():
        raise Http404
    return newsletter_subscribe_request(
        request, newsletter_slug=newsletter_slug
    )


def newsletter_subscribe_request(request, newsletter_slug=None):
    newsletter = get_object_or_404(
        Newsletter,
        slug=newsletter_slug or settings.DEFAULT_NEWSLETTER
    )

    if request.method == 'POST':
        form = NewsletterForm(
            data=request.POST, request=request,
        )
        if form.is_valid():
            result, subscriber = form.save(newsletter, request.user)

            if request.is_ajax():
                # No-CSRF ajax request
                # are allowed to access current user
                if request.user.is_authenticated:
                    if result == SubscriptionResult.ALREADY_SUBSCRIBED:
                        return HttpResponse(content='''<div class="alert alert-info" role="alert">
                        Sie haben unseren Newsletter schon abonniert!
                        </div>'''.encode('utf-8'))
                    elif result == SubscriptionResult.SUBSCRIBED:
                        return HttpResponse(content='''<div class="alert alert-primary" role="alert">
                        Sie haben unseren Newsletter erfolgreich abonniert!
                        </div>'''.encode('utf-8'))

                return HttpResponse(content='''<div class="alert alert-primary" role="alert">
                Sie haben eine E-Mail erhalten, um Ihr Abonnement zu bestätigen.
                </div>'''.encode('utf-8'))

            if result == SubscriptionResult.CONFIRM:
                messages.add_message(
                    request, messages.INFO,
                    'Sie haben eine E-Mail erhalten, um Ihr Abonnement zu bestätigen.'
                )

            return get_redirect(request, default='/')
        else:
            messages.add_message(
                request, messages.WARNING,
                'Bitte überprüfen Sie Ihre Eingabe.'
            )
    else:
        form = NewsletterForm(request=request, initial={
            'email': request.GET.get('email', '')
        })

    if request.is_ajax():
        url = '{}?{}'.format(
            reverse('fds_newsletter_subscribe_request', kwargs={
                'newsletter_slug': newsletter.slug
            }),
            urlencode({'email': form.data.get('email', '')})
        )
        return HttpResponse(url)
    return render(request, "fds_newsletter/subscribe.html", {
        'newsletter': newsletter,
        'form': form
    })


def confirm_subscribe(request, newsletter_slug=None, pk=None, activation_code=None):
    newsletter = get_object_or_404(
        Newsletter, slug=newsletter_slug
    )
    subscriber = get_object_or_404(
        Subscriber, newsletter=newsletter, pk=pk,
        activation_code=activation_code
    )
    subscriber.subscribe()
    messages.add_message(
        request, messages.INFO,
        'Sie erhalten nun den %s' % newsletter.title
    )

    return redirect(newsletter.url or '/')


def confirm_unsubscribe(request, newsletter_slug=None, pk=None, activation_code=None):
    newsletter = get_object_or_404(
        Newsletter, slug=newsletter_slug
    )
    subscriber = get_object_or_404(
        Subscriber, newsletter=newsletter, pk=pk,
        activation_code=activation_code
    )
    subscriber.unsubscribe(method='unsubscribe-link')
    messages.add_message(
        request, messages.INFO,
        'Sie erhalten den %s nun nicht mehr.' % newsletter.title
    )

    return redirect(newsletter.url or '/')


@require_POST
@login_required
def newsletter_user_settings(request):
    form = NewslettersUserForm(request.user, request.POST)
    if form.is_valid():
        form.save()
        messages.add_message(
            request, messages.SUCCESS,
            'Ihre Newsletter-Abonnements wurden aktualisiert.'
        )

    return redirect('account-settings')
