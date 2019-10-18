from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.views.generic.edit import FormView

from froide.helper.utils import get_redirect

from .forms import DonationGiftForm, DonationFormFactory


@require_POST
def make_order(request, category):
    form = DonationGiftForm(data=request.POST, category=category)
    if form.is_valid():
        form.save(request)
        return get_redirect(request)

    messages.add_message(request, messages.ERROR, 'Form-Fehler!')
    return get_redirect(request, next=request.META.get('HTTP_REFERER', '/'))


class DonationView(FormView):
    template_name = 'fds_donation/forms/donation.html'

    def get_form_action(self):
        return reverse('fds_donation:donate')

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""

        form_kwargs = self.get_form_kwargs()
        form_factory = DonationFormFactory()
        form = form_factory.make_form(
            user=self.request.user,
            action=self.get_form_action(),
            **form_kwargs
        )
        return form

    def form_valid(self, form):
        order, related_obj = form.save()
        method = form.cleaned_data['payment_method']
        return redirect(order.get_absolute_payment_url(method))
