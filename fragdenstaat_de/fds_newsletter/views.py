from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from newsletter.views import (
    NewsletterListView, SubmissionArchiveDetailView,
    SubmissionArchiveIndexView
)
from newsletter.forms import SubscribeRequestForm
from newsletter.models import Newsletter, Subscription

from froide.helper.utils import get_client_ip


@require_POST
@csrf_exempt
def newsletter_ajax_subscribe_request(request, newsletter_slug=None):
    if not request.is_ajax():
        # Only ajax requests can be reasonably csrf exempt
        return HttpResponse(status_code=403)

    newsletter = get_object_or_404(
        Newsletter,
        slug=newsletter_slug or settings.DEFAULT_NEWSLETTER
    )
    email_confirmed = False
    email = request.POST.get('email_field', '')
    if request.user.is_authenticated and request.user.is_active:
        if request.user.email == email:
            email_confirmed = True

    if email_confirmed:
        already = subscribe_user(request, newsletter)
        if already:
            return HttpResponse(content='''<div class="alert alert-info" role="alert">
            Sie haben unseren Newsletter schon abonniert!
            </div>'''.encode('utf-8'))
        else:
            return HttpResponse(content='''<div class="alert alert-primary" role="alert">
            Sie haben unseren Newsletter erfolgreich abonniert!
            </div>'''.encode('utf-8'))

    result = subscribe_email(request, newsletter)
    if result:
        return HttpResponse(content='''<div class="alert alert-primary" role="alert">
            Sie haben eine E-Mail erhalten, um Ihr Abonnement zu bestätigen.
            </div>'''.encode('utf-8'))
    return HttpResponse(newsletter.get_absolute_url().encode('utf-8'))


def subscribe_email(request, newsletter):
    form = SubscribeRequestForm(
        data=request.POST,
        newsletter=newsletter,
        ip=get_client_ip(request)
    )
    if form.is_valid():
        subscription = form.save()
        subscription.send_activation_email(action='subscribe')
        return True
    return False


def subscribe_user(request, newsletter):
    already_subscribed = False
    instance = Subscription.objects.get_or_create(
        newsletter=newsletter, user=request.user
    )[0]

    if instance.subscribed:
        already_subscribed = True
    else:
        instance.subscribed = True
        instance.save()
    return already_subscribed


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
