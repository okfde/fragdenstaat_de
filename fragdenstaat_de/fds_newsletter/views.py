from django.http import HttpResponse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from newsletter.views import (
    NewsletterListView, SubmissionArchiveDetailView,
    SubmissionArchiveIndexView
)
from newsletter.models import Newsletter

from .utils import subscribe, SubscriptionResult


@require_POST
@csrf_exempt
def newsletter_ajax_subscribe_request(request, newsletter_slug=None):
    newsletter = get_object_or_404(
        Newsletter,
        slug=newsletter_slug or settings.DEFAULT_NEWSLETTER
    )

    email = request.POST.get('email_field', '')
    if not email:
        if request.is_ajax():
            return HttpResponse(newsletter.get_absolute_url().encode('utf-8'))
        return redirect(newsletter.get_absolute_url())

    result = subscribe(newsletter, email, user=request.user)

    if request.is_ajax():
        # No-CSRF ajax request
        # are allowed to access current user
        if result == SubscriptionResult.ALREADY_SUBSCRIBED:
            return HttpResponse(content='''<div class="alert alert-info" role="alert">
            Sie haben unseren Newsletter schon abonniert!
            </div>'''.encode('utf-8'))
        elif result == SubscriptionResult.SUBSCRIBED:
            return HttpResponse(content='''<div class="alert alert-primary" role="alert">
            Sie haben unseren Newsletter erfolgreich abonniert!
            </div>'''.encode('utf-8'))
        elif result == SubscriptionResult.CONFIRM:
            return HttpResponse(content='''<div class="alert alert-primary" role="alert">
            Sie haben eine E-Mail erhalten, um Ihr Abonnement zu bestätigen.
            </div>'''.encode('utf-8'))
        return HttpResponse(newsletter.get_absolute_url().encode('utf-8'))

    if result == SubscriptionResult.CONFIRM:
        messages.add_message(
            request, messages.INFO,
            'Sie haben eine E-Mail erhalten, um Ihr Abonnement zu bestätigen.'
        )

    return redirect(newsletter.get_absolute_url())


@require_POST
def newsletter_user_settings(request):
    view = NewsletterListView.as_view()
    view(request)
    return redirect('account-settings')


class NicerSubmissionArchiveDetailView(SubmissionArchiveDetailView):
    template_name = 'fds_newsletter/submission_detail.html'

    def render_to_response(self, context, **response_kwargs):
        return super(SubmissionArchiveDetailView, self).render_to_response(
            context, **response_kwargs
        )


class NicerSubmissionArchiveIndexView(SubmissionArchiveIndexView):
    template_name = 'fds_newsletter/submission_archive.html'
