from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView, UpdateView
from django.views.generic.edit import FormView

from froide.helper.breadcrumbs import Breadcrumbs, BreadcrumbView
from froide.helper.utils import get_redirect, is_ajax

from .form_settings import DonationFormFactory, DonationSettingsForm
from .forms import (
    DonationGiftForm,
    DonorDetailsForm,
    QuickDonationForm,
    SimpleDonationForm,
)
from .models import DonationFormViewCount, Donor
from .services import confirm_donor_email, merge_donor_list


@require_POST
def make_order(request, category):
    form = DonationGiftForm(data=request.POST, category=category, request=request)
    if form.is_valid():
        messages.add_message(request, messages.SUCCESS, "Danke für Deine Bestellung!")
        form.save(request)
        return get_redirect(request)

    messages.add_message(request, messages.ERROR, "Form-Fehler!")
    return get_redirect(request, next=request.META.get("HTTP_REFERER", "/"))


class DonationView(FormView):
    template_name = "fds_donation/forms/donation.html"

    def get_form_action(self):
        return reverse("fds_donation:donate")

    def get(self, request, *args, **kwargs):
        DonationFormViewCount.objects.handle_request(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if is_ajax(request):
            return quick_donation(request)
        return super().post(request, *args, **kwargs)

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""

        form_kwargs = self.get_form_kwargs()
        form_factory = DonationFormFactory(
            reference=self.request.GET.get("pk_campaign", ""),
            keyword=self.request.GET.get("pk_keyword", ""),
        )
        form = form_factory.make_form(
            user=self.request.user,
            request=self.request,
            action=self.get_form_action(),
            **form_kwargs,
        )
        return form

    def form_valid(self, form):
        order, related_obj = form.save()
        method = form.cleaned_data["payment_method"]
        return redirect(order.get_absolute_payment_url(method))


def quick_donation(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    form = QuickDonationForm(
        data=request.POST,
        user=request.user,
        request=request,
    )
    if form.is_valid():
        order, related_obj = form.save()

        payment = order.get_or_create_payment(form.payment_method, request=request)
        provider = payment.get_provider()
        result = provider.start_quick_payment(payment)
        result["successurl"] = settings.SITE_URL + payment.get_success_url()

        return JsonResponse(result)
    return JsonResponse(
        {
            "error": form.errors.as_text(),
        },
        status=400,
    )


def get_base_breadcrumb(donor):
    return Breadcrumbs(
        items=[(_("My donations"), donor.get_absolute_url())], color="yellow-200"
    )


class DonationCompleteView(TemplateView):
    template_name = "fds_donation/donation_complete.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["order"] = self.request.GET.get("order", "")
        ctx["receipt"] = self.request.GET.get("receipt", "")
        ctx["subscription"] = self.request.GET.get("subscription", "")
        ctx["email"] = self.request.GET.get("email", "")
        return ctx


class DonationFailedView(TemplateView):
    template_name = "fds_donation/donation_failed.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["donate_url"] = reverse("fds_donation:donate")
        return ctx


class DonorMixin:
    model = Donor
    slug_field = "uuid"
    slug_url_kwarg = "token"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        response = self.should_redirect_user()
        if response:
            return response
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        response = self.should_redirect_user()
        if response:
            return response
        return super().post(request, *args, **kwargs)

    def should_redirect_user(self):
        is_auth = self.request.user.is_authenticated
        has_token = "token" in self.kwargs
        is_same_user = self.object.user == self.request.user
        if is_auth and has_token and is_same_user:
            # User is logged in and donor user, redirect to user view
            return redirect(self.get_user_url())
        return None

    def get_user_url(self):
        return reverse("fds_donation:donor-user")

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        if not obj.email_confirmed:
            confirm_donor_email(obj, request=self.request)

        return obj


class DonorView(DonorMixin, DetailView, BreadcrumbView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        donations = self.object.donations.filter(completed=True).select_related(
            "recurrence", "donationgiftorder__donation_gift"
        )
        try:
            last_donation = donations[0]
        except IndexError:
            last_donation = None

        has_pending = any(
            not d.received_timestamp and d.method == "banktransfer" for d in donations
        )

        donation_downloads = sorted(
            {
                dl
                for d in donations
                if hasattr(d, "donationgiftorder")
                and (dl := d.donationgiftorder.get_donation_download())
            }
        )

        ctx.update(
            {
                "recurrences": self.object.recurrences.filter(cancel_date=None),
                "donations": donations,
                "last_donation": last_donation,
                "has_pending": has_pending,
                "donation_downloads": donation_downloads,
            }
        )
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if not context["last_donation"]:
            return redirect(self.object.get_absolute_donate_url())
        return super().render_to_response(context, **response_kwargs)

    def get_breadcrumbs(self, context):
        return get_base_breadcrumb(context["object"])


class DonorUserMixin:
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object is None:
            return self.no_donor_found(request)
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object is None:
            return self.no_donor_found(request)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def no_donor_found(self, request):
        messages.add_message(
            request,
            messages.INFO,
            _(
                "We have no associated donations with your account. "
                "If you have donated, let us know! "
                "Otherwise feel free to donate below."
            ),
        )
        return redirect("/spenden/")

    def get_object(self, queryset=None):
        donors = Donor.objects.filter(
            user=self.request.user, email_confirmed__isnull=False
        )
        if len(donors) == 0:
            return None
        if len(donors) == 1:
            return donors[0]
        return merge_donor_list(donors)


class DonorUserView(LoginRequiredMixin, DonorUserMixin, DonorView):
    pass


class DonorChangeView(DonorMixin, UpdateView, BreadcrumbView):
    form_class = DonorDetailsForm

    def form_valid(self, form):
        messages.add_message(
            self.request, messages.SUCCESS, _("Your donor info has been updated!")
        )
        return super().form_valid(form)

    def get_user_url(self):
        return reverse("fds_donation:donor-user-change")

    def get_breadcrumbs(self, context):
        return get_base_breadcrumb(context["object"]) + [
            (_("Change your details"), context["object"].get_absolute_change_url())
        ]


class DonorChangeUserView(LoginRequiredMixin, DonorUserMixin, DonorChangeView):
    pass


class DonorDonationActionView(DonorMixin, UpdateView, BreadcrumbView):
    form_class = SimpleDonationForm
    template_name = "fds_donation/donation_form.html"

    def get_user_url(self):
        return reverse("fds_donation:donor-user-donate")

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        del form_kwargs["instance"]
        return form_kwargs

    def get_form(self, form_class=...):
        donor = self.object
        self.has_subscription = donor.has_active_subscription()
        if self.has_subscription:
            form_settings = {"interval": "recurring"}
        else:
            form_settings = {"interval": "once_recurring"}

        request_data = DonationFormFactory.from_request(self.request)
        form_settings.update(request_data)
        form = DonationSettingsForm(data=form_settings)
        return form.make_donation_form(
            form_class=self.form_class,
            request=self.request,
            user=self.request.user,
            action=self.request.path,
            **self.get_form_kwargs(),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "recurrences": self.object.recurrences.filter(cancel_date=None),
                "has_donation": self.object.donations.filter(completed=True).exists(),
            }
        )
        return context

    def form_valid(self, form):
        extra_data = {"donor": self.object, **self.object.get_form_data()}
        order, related_obj = form.save(extra_data=extra_data)
        method = form.cleaned_data["payment_method"]
        return redirect(order.get_absolute_payment_url(method))

    def form_invalid(self, form):
        messages.add_message(self.request, messages.ERROR, "Form-Fehler!")
        return super().form_invalid(form)

    def get_breadcrumbs(self, context):
        if context.get("has_donation", True):
            return get_base_breadcrumb(context["object"]) + [
                (_("Donate"), context["object"].get_absolute_donate_url())
            ]
        return []


class DonorDonationActionUserView(
    LoginRequiredMixin, DonorUserMixin, DonorDonationActionView
):
    pass
