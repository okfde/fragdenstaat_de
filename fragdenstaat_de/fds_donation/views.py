from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView, UpdateView
from django.views.generic.edit import FormView

from froide.helper.breadcrumbs import Breadcrumbs, BreadcrumbView
from froide.helper.utils import (
    get_redirect,
    get_redirect_url,
    is_ajax,
    update_query_params,
)

from fragdenstaat_de.fds_donation.utils import validate_donor_token

from .form_settings import DonationFormFactory, DonationSettingsForm
from .forms import (
    DonationGiftForm,
    DonorDetailsForm,
    DonorEmailLinkForm,
    QuickDonationForm,
    SimpleDonationForm,
)
from .models import DonationFormViewCount, Donor
from .services import confirm_donor_email
from .utils import DONOR_SESSION_KEY, get_donor_from_request


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

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object is None:
            return self.no_donor_found(request)
        return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object is None:
            return self.no_donor_found(request)
        confirm_donor_email(self.object, request=self.request)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def no_donor_found(self, request):
        if self.request.user.is_authenticated:
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
        else:
            return redirect("fds_donation:donor-send-login-link")

    def get_object(self, queryset=None):
        donor = get_donor_from_request(self.request)
        if self.request.user.is_authenticated and donor is not None:
            if donor.user and donor.user != self.request.user:
                messages.add_message(
                    self.request,
                    messages.WARNING,
                    _(
                        "You are logged in with a different account than the one associated with this donor."
                    ),
                )

        return donor


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
            return redirect("fds_donation:donor-donate")
        return super().render_to_response(context, **response_kwargs)

    def get_breadcrumbs(self, context):
        return get_base_breadcrumb(context["object"])


class DonorChangeView(DonorMixin, UpdateView, BreadcrumbView):
    form_class = DonorDetailsForm

    def form_valid(self, form):
        messages.add_message(
            self.request, messages.SUCCESS, _("Your donor info has been updated!")
        )
        return super().form_valid(form)

    def get_breadcrumbs(self, context):
        return get_base_breadcrumb(context["object"]) + [
            (_("Change your details"), context["object"].get_absolute_change_url())
        ]


class DonorDonationActionView(DonorMixin, UpdateView, BreadcrumbView):
    form_class = SimpleDonationForm
    template_name = "fds_donation/donation_form.html"

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


def donor_login(request, donor_id, token, next_path):
    if next_path == "/":
        # If no further path is given, try extracting next parameter
        next_path = get_redirect_url(request, default=next_path)
    # TODO: carry query params to next?
    if request.method == "POST":
        donor, valid = validate_donor_token(donor_id, token)
        if not valid:
            # Token expired or invalid
            messages.add_message(
                request,
                messages.WARNING,
                _("Your link has expired, please request a new one."),
            )
            return redirect("fds_donation:donor-send-login-link")
        if donor.user and request.user.is_authenticated:
            if donor.user != request.user:
                messages.add_message(
                    request,
                    messages.ERROR,
                    _("You cannot access this donor with the current account."),
                )
            return redirect(next_path)

        donor.update_last_login()
        request.session[DONOR_SESSION_KEY] = donor.id

        return redirect(next_path)

    return render(
        request,
        "account/go.html",
        {
            "form_action": request.get_full_path(),
            "next": next_path,
        },
    )


def get_legacy_redirect(url_name):
    def redirect_legacy_donor_view(request, token):
        path = reverse(url_name)
        return redirect(
            update_query_params(
                reverse("fds_donation:donor-send-login-link"), {"next": path}
            )
        )

    return redirect_legacy_donor_view


def send_donor_login_link(request):
    if request.method == "POST":
        form = DonorEmailLinkForm(request.POST)
        if form.is_valid():
            form.send_login_link()
            messages.add_message(
                request,
                messages.SUCCESS,
                _("We have sent you a link to access your donations."),
            )
            return redirect("/")
    else:
        form = DonorEmailLinkForm(initial={"next_path": get_redirect_url(request)})

    return render(request, "fds_donation/donor_login_link_form.html", {"form": form})


def donor_logout(request):
    if request.method == "POST":
        del request.session[DONOR_SESSION_KEY]
    return redirect("/")
