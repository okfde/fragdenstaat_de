from urllib.parse import urlencode

from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, Http404, render
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ArchiveIndexView, DateDetailView

from newsletter.views import NewsletterListView, SubscribeRequestView as DNSubscribeRequestView
from newsletter.models import Newsletter

from froide.helper.utils import get_redirect

from fragdenstaat_de.fds_mailing.models import Mailing

from .forms import NewsletterForm
from .utils import subscribe, SubscriptionResult


class SubscribeRequestView(DNSubscribeRequestView):
    form_class = NewsletterForm


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
            email = form.cleaned_data['email']
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
                return HttpResponse('/')

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


@require_POST
def newsletter_user_settings(request):
    view = NewsletterListView.as_view()
    view(request)
    return redirect('account-settings')


class NewsletterEditionMixin:
    date_field = 'sending_date'
    date_list_period = 'month'
    allow_empty = True

    year_format = '%Y'
    month_format = '%m'
    day_format = '%d'

    def dispatch(self, *args, **kwargs):
        newsletter_slug = kwargs['newsletter_slug']
        self.newsletter = get_object_or_404(
            Newsletter.on_site.filter(visible=True),
            slug=newsletter_slug,
        )
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        return Mailing.objects.filter(
            publish=True, ready=True, submitted=True,
            newsletter__slug=settings.DEFAULT_NEWSLETTER
        )

    def get_context_data(self, **kwargs):
        """ Add newsletter to context. """
        context = super().get_context_data(**kwargs)

        context['newsletter'] = self.newsletter

        return context


class NicerSubmissionArchiveIndexView(NewsletterEditionMixin, ArchiveIndexView):
    template_name = 'fds_newsletter/archive.html'


class NicerSubmissionArchiveDetailView(NewsletterEditionMixin, DateDetailView):
    template_name = 'fds_newsletter/detail.html'

    def get_context_data(self, **kwargs):
        """
        Make sure the actual message is available.
        """
        context = super().get_context_data(**kwargs)

        message = self.object.email_template

        context.update({
            'message': message,
            'content': message.get_body_html(
                template='fds_mailing/render_browser.html'
            ),
            'date': self.object.sending_date,
        })

        return context
