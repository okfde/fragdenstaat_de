import tempfile
import uuid
from collections import defaultdict

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.views.main import ChangeList
from django.core.exceptions import PermissionDenied
from django.db.models import (
    Aggregate,
    Avg,
    Count,
    Exists,
    F,
    Max,
    OuterRef,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Concat
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import formats, timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from adminsortable2.admin import SortableAdminMixin
from flowcontrol.engine import start_flowrun
from flowcontrol.models import Flow
from froide_payment.models import PaymentStatus

from froide.helper.admin_utils import (
    ForeignKeyFilter,
    make_batch_tag_action,
    make_choose_object_action,
    make_daterangefilter,
    make_emptyfilter,
    make_nullfilter,
    make_rangefilter,
)
from froide.helper.auth import is_crew
from froide.helper.csv_utils import dict_to_csv_stream, export_csv_response
from froide.helper.widgets import TagAutocompleteWidget

from fragdenstaat_de.fds_mailing.models import MailingMessage
from fragdenstaat_de.fds_mailing.utils import SetupMailingMixin
from fragdenstaat_de.fds_newsletter.admin_utils import make_subscriber_tagger
from fragdenstaat_de.theme.admin import make_tag_autocomplete_admin

from .admin_utils import (
    ActiveRecurrencesListFilter,
    DonorProjectFilter,
    DonorTagListFilter,
    DonorTotalAmountPerYearFilter,
    PassiveDonationListFilter,
)
from .export import JZWBExportForm
from .models import (
    DONATION_PROJECTS,
    DefaultDonation,
    DeferredDonation,
    Donation,
    DonationFormCMSPlugin,
    DonationFormViewCount,
    DonationGift,
    DonationGiftOrder,
    Donor,
    DonorTag,
    Recurrence,
)
from .services import send_donation_gift_order_shipped


def median(field):
    return Aggregate(
        F(field),
        function="percentile_cont",
        template="%(function)s(0.5) WITHIN GROUP (ORDER BY %(expressions)s)",
    )


DONOR_TAG_AUTOCOMPLETE = make_tag_autocomplete_admin(
    DonorTag, "fds_donation-donortag-autocomplete"
)


class DonorAdminForm(forms.ModelForm):
    class Meta:
        model = Donor
        fields = "__all__"
        widgets = {
            "tags": TagAutocompleteWidget(autocomplete_url=DONOR_TAG_AUTOCOMPLETE),
        }


class DonorChangeList(ChangeList):
    def get_results(self, *args, **kwargs):
        ret = super().get_results(*args, **kwargs)

        last_year = timezone.now().year - 1
        q = self.queryset.aggregate(
            amount_total_sum=Sum("amount_total"),
            amount_last_year_sum=Sum("amount_last_year"),
            amount_total_median=median("amount_total"),
            amount_total_avg=Avg("amount_total"),
            amount_last_year_avg=Avg("amount_last_year"),
            recurring_total=Sum("recurring_amount"),
            duplicates=Count(
                "duplicate",
                distinct=True,
                filter=Q(
                    duplicate__isnull=False,
                    donations__received_timestamp__year=last_year,
                ),
            ),
        )
        self.amount_total_sum = q["amount_total_sum"]
        self.amount_total_avg = (
            round(q["amount_total_avg"]) if q["amount_total_avg"] is not None else "-"
        )
        self.amount_last_year_sum = q["amount_last_year_sum"]
        self.amount_last_year_avg = (
            round(q["amount_last_year_avg"])
            if q["amount_last_year_avg"] is not None
            else "-"
        )
        self.amount_total_median = (
            round(q["amount_total_median"])
            if q["amount_total_median"] is not None
            else "-"
        )
        self.total_amount_recurring = q["recurring_total"]
        self.duplicates = q["duplicates"] or 0
        return ret


@admin.register(Donor)
class DonorAdmin(SetupMailingMixin, admin.ModelAdmin):
    form = DonorAdminForm

    list_display = (
        "get_name",
        "admin_link_donations",
        "city",
        "active",
        "last_donation",
        "amount_total",
        "amount_last_year",
        "recurring_amount",
        "donation_count",
        "receipt",
    )
    list_filter = (
        "active",
        make_nullfilter("recurrences", _("Has recurring donations")),
        ActiveRecurrencesListFilter,
        DonorTotalAmountPerYearFilter,
        make_rangefilter("recurring_amount", _("recurring monthly amount")),
        make_daterangefilter("recurrence_streak_start", _("Recurrence streak start")),
        make_daterangefilter("last_donation", _("Last donation")),
        "subscriber__subscribed",
        "email_confirmed",
        "become_user",
        "receipt",
        "invalid",
        DonorProjectFilter,
        make_emptyfilter("company_name", _("has company name")),
        make_emptyfilter("email", _("has email")),
        make_nullfilter("duplicate", _("has duplicate")),
        make_nullfilter("user_id", _("has user")),
        ("user", ForeignKeyFilter),
        DonorTagListFilter,
        ("id", ForeignKeyFilter),
    )
    date_hierarchy = "first_donation"
    search_fields = (
        "email",
        "last_name",
        "first_name",
        "company_name",
        "identifier",
        "note",
    )
    raw_id_fields = ("user", "subscriptions", "subscriber")

    readonly_fields = (
        "first_donation",
        "email_confirmation_sent",
        "become_user",
        "subscriber",
        "amount_total",
        "amount_last_year",
        "donation_count",
        "last_donation",
        "render_recurrences",
    )

    fieldsets = (
        (
            _("Donor"),
            {
                "fields": (
                    "email",
                    "salutation",
                    (
                        "first_name",
                        "last_name",
                    ),
                    "company_name",
                    "address",
                    (
                        "postcode",
                        "city",
                    ),
                    "country",
                    "user",
                )
            },
        ),
        (
            _("Contact"),
            {
                "fields": (
                    "email_confirmation_sent",
                    "email_confirmed",
                    "contact_allowed",
                    "receipt",
                    "invalid",
                    "note",
                    "tags",
                )
            },
        ),
        (
            _("Stats"),
            {
                "fields": (
                    "first_donation",
                    "amount_total",
                    "amount_last_year",
                    "recurring_amount",
                    "recurrence_streak_start",
                    "donation_count",
                    "last_donation",
                    "render_recurrences",
                )
            },
        ),
        (
            _("Advanced"),
            {
                "fields": (
                    "active",
                    "subscriptions",
                    "subscriber",
                    "become_user",
                    "identifier",
                    "attributes",
                ),
                "classes": ("collapse", "collapse-closed"),
            },
        ),
    )

    actions = [
        "send_donor_optin_email",
        "merge_donors",
        "detect_duplicates",
        "clear_duplicates",
        "export_jzwb",
        "detect_recurring_on_donor",
        "tag_all",
        "mark_invalid_addresses",
        "export_donor_csv",
        "tag_subscribers",
        "start_flow_on_donor",
    ] + SetupMailingMixin.actions

    tag_all = make_batch_tag_action(autocomplete_url=DONOR_TAG_AUTOCOMPLETE)
    tag_subscribers = make_subscriber_tagger(
        lambda qs: qs.exclude(email="").values_list("email", flat=True)
    )
    start_flow_on_donor = make_choose_object_action(
        Flow.objects.get_active(),
        lambda admin, request, qs, obj: [start_flowrun(obj, donor) for donor in qs],
        _("Start workflow for donors..."),
    )

    def get_changelist(self, request):
        return DonorChangeList

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "merge-donors/",
                self.admin_site.admin_view(self.merge_donor_view),
                name="fds_donation-donor-merge_donor",
            ),
        ]
        return my_urls + urls

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("subscriber")
        donations_filter = Q(donations__received_timestamp__isnull=False)

        donation_projects = request.GET.get(DonorProjectFilter.parameter_name)
        any_donation = {}
        if donation_projects:
            values = donation_projects.split(",")
            project_q = DonorProjectFilter.get_q(values, "donations__project__in")
            donations_filter &= project_q
            any_donation = {"any_donation": Count("donations", filter=project_q)}

        last_year = timezone.now().year - 1
        qs = qs.annotate(
            amount_total=Sum("donations__amount", filter=donations_filter),
            amount_last_year=Sum(
                "donations__amount",
                filter=donations_filter
                & Q(donations__received_timestamp__year=last_year),
            ),
            donation_count=Count("donations", filter=donations_filter),
            last_donation=Max("donations__timestamp", filter=donations_filter),
            **any_donation,
        )
        if donation_projects:
            qs = qs.filter(any_donation__gt=0)
        return qs

    def view_on_site(self, obj):
        return reverse("fds_donation:donor-legacy", kwargs={"token": obj.uuid})

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.user and is_crew(obj.user):
            # Allow recurring amount change on crew donors for testing
            return self.readonly_fields
        return self.readonly_fields + ("recurring_amount", "recurrence_streak_start")

    @admin.display(ordering="donation_count", description=_("Donation count"))
    def donation_count(self, obj):
        return obj.donation_count

    @admin.display(ordering="amount_total", description=_("Amount total"))
    def amount_total(self, obj):
        return formats.number_format(obj.amount_total or 0, decimal_pos=2)

    @admin.display(ordering="amount_last_year", description=_("Amount last year"))
    def amount_last_year(self, obj):
        return formats.number_format(obj.amount_last_year or 0, decimal_pos=2)

    @admin.display(ordering="last_donation", description=_("Last donation"))
    def last_donation(self, obj):
        return obj.last_donation

    @admin.display(
        ordering=Concat("first_name", Value(" "), "last_name"), description=_("Name")
    )
    def get_name(self, obj):
        return str(obj)

    @admin.display(description=_("donations"))
    def admin_link_donations(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:fds_donation_donation_changelist") + ("?donor=%s" % obj.pk),
            _("donations"),
        )

    @admin.display(description=_("Recurrences"))
    def render_recurrences(self, obj):
        recurrences = obj.recurrences.all()
        if not recurrences:
            return mark_safe("<em>-</em>")

        def render_recurrence(recurrence):
            if recurrence.subscription_id:
                return format_html(
                    '<a href="{}">{}</a>',
                    reverse(
                        "admin:froide_payment_subscription_change",
                        args=(recurrence.subscription_id,),
                    ),
                    recurrence.get_description(),
                )
            return format_html("{}", recurrence.get_description())

        items = mark_safe(
            "</li><li>".join(
                render_recurrence(recurrence) for recurrence in recurrences
            )
        )
        return format_html("<ul>{}</ul>", items)

    @admin.action(description=_("Send opt-in mail"))
    def send_donor_optin_email(self, request, queryset):
        from .services import send_donor_optin_email

        count = 0
        for donor in queryset:
            if send_donor_optin_email(donor):
                count += 1

        self.message_user(
            request,
            _("Send {count} optin mails.").format(count=count),
            level=messages.INFO,
        )

    @admin.action(description=_("Clear duplicate flag on donors"))
    def clear_duplicates(self, request, queryset):
        # Clear order of queryset to avoid ordering on non-existing annotation columns
        queryset.order_by().update(duplicate=None)
        self.message_user(request, _("Duplicate flags cleared."))

    @admin.action(description=_("Detect duplicate donors"))
    def detect_duplicates(self, request, queryset):
        key_funcs = {
            "email": lambda obj: obj.email if obj.email else None,
            "name_addres": lambda obj: (
                (
                    obj.get_full_name(),
                    obj.address,
                    obj.postcode,
                    obj.city,
                )
                if obj.address and obj.get_full_name()
                else None
            ),
            "iban": lambda obj: (
                obj.attributes.get("iban")
                if obj.attributes and obj.attributes.get("iban")
                else None
            ),
        }
        dupe_lists = {key: defaultdict(list) for key in key_funcs.keys()}
        id_sets = defaultdict(set)

        for obj in queryset:
            for key_name, key_func in key_funcs.items():
                key = key_func(obj)
                if key:
                    dupe_lists[key_name][key].append(obj.id)

        for _key, dupe_dict in dupe_lists.items():
            for id_list in dupe_dict.values():
                if len(id_list) > 1:
                    id_set = set()
                    for donor_id in id_list:
                        if donor_id in id_sets:
                            id_set.update(id_sets[donor_id])
                        id_set.add(donor_id)
                        id_sets[donor_id] = id_set
        already = set()
        count = 0
        for donor_id, id_set in id_sets.items():
            if donor_id in already:
                continue
            already.update(id_set)
            Donor.objects.filter(id__in=id_set).update(duplicate=uuid.uuid4())
            count += 1
        self.message_user(
            request,
            _("Detected {dup} duplicate sets with {donors} donors").format(
                dup=count, donors=len(already)
            ),
        )

    @admin.action(description=_("Mark invalid addresses"))
    def mark_invalid_addresses(self, request, queryset):
        qs = queryset.filter(
            Q(postcode="")
            | Q(address="")
            | Q(city="")
            | Q(last_name="")
            | ~(Q(postcode__regex=r"^\d{5}$") | ~Q(country="DE"))
        )
        # Clear order of queryset to avoid ordering on non-existing annotation columns
        qs.order_by().update(invalid=True)

    def merge_donor_view(self, request):
        """
        Render the merge donor view.
        """
        if not self.has_change_permission(request):
            raise PermissionDenied

        auto_next = request.GET.get("auto_next")

        donor_ids = request.GET.get("donor_id", "")
        donor_ids = [donor_id for donor_id in donor_ids.split(",") if donor_id]
        if not auto_next and not donor_ids:
            self.message_user(request, _("No donors selected!"))
            return redirect("admin:fds_donation_donor_changelist")
        elif auto_next:
            last_year = timezone.now().year - 1
            donations = Donation.objects.filter(
                received_timestamp__year=last_year, donor_id=OuterRef("pk")
            )

            first_donor = (
                Donor.objects.filter(duplicate__isnull=False)
                .filter(Exists(donations))
                .order_by("?")
                .first()
            )
            if not first_donor:
                self.message_user(request, _("No duplicate donors found!"))
                return redirect("admin:fds_donation_donor_changelist")
            queryset = Donor.objects.filter(duplicate=first_donor.duplicate)
        else:
            queryset = Donor.objects.filter(id__in=donor_ids)

        response = self.merge_donors(request, queryset)
        if response:
            return response
        return redirect("admin:fds_donation_donor_changelist")

    @admin.action(description=_("Merge donors"))
    def merge_donors(self, request, queryset):
        """
        Send mail to users

        """
        from .forms import get_merge_donor_form
        from .utils import merge_donors, propose_donor_merge

        if request.POST:
            select_across = request.POST.get("select_across", "0") == "1"
            if select_across:
                self.message_user(request, _("Select across not allowed!"))
                return

        last_year = timezone.now().year - 1
        donations_filter = Q(donations__received_timestamp__isnull=False)
        candidates = queryset.order_by("-id").annotate(
            amount_total=Sum("donations__amount", filter=donations_filter),
            amount_last_year=Sum(
                "donations__amount",
                filter=donations_filter
                & Q(donations__received_timestamp__year=last_year),
            ),
            donation_count=Count("donations", filter=donations_filter),
        )
        candidate_ids = [x.id for x in candidates]
        if len(candidate_ids) < 2:
            self.message_user(request, _("Need to select more than one!"))
            return

        MergeDonorForm = get_merge_donor_form(self.admin_site)

        donor_form = None
        if request.POST and "salutation" in request.POST:
            donor = None
            if request.POST.get("cancel"):
                candidates.update(duplicate=None)
            else:
                donor_form = MergeDonorForm(data=request.POST)
                if donor_form.is_valid():
                    primary_id = None
                    if request.POST.get("primary") is not None:
                        primary_id = request.POST["primary"]
                        if primary_id not in candidate_ids:
                            primary_id = None
                    if primary_id is None:
                        primary_id = candidate_ids[0]

                    donor = merge_donors(
                        candidates, primary_id, donor_form.cleaned_data
                    )

                    self.message_user(
                        request,
                        _("Merged {count} donors into {donor}").format(
                            count=len(candidates), donor=donor
                        ),
                    )
            if request.POST.get("auto_next"):
                return redirect(
                    reverse("admin:fds_donation-donor-merge_donor") + "?auto_next=1"
                )
            if donor is None:
                return redirect("admin:fds_donation_donor_changelist")
            return redirect("admin:fds_donation_donor_change", donor.id)

        if donor_form is None:
            merged_donor = propose_donor_merge(candidates, MergeDonorForm.Meta.fields)
            donor_form = MergeDonorForm(instance=merged_donor)

        context = {
            "opts": self.model._meta,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "queryset": candidates,
            "form": donor_form,
        }

        # Display the confirmation page
        return TemplateResponse(
            request, "admin/fds_donation/donor/merge_donors.html", context
        )

    @admin.action(
        description=_("Export JZWB..."),
    )
    def export_jzwb(self, request, queryset):
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        form = JZWBExportForm(request.POST or None)
        if request.POST.get("year"):
            form = JZWBExportForm(request.POST)
            if form.is_valid():
                response = form.make_response(queryset)
                if response is None:
                    count = queryset.count()
                    self.message_user(
                        request,
                        _("Sending JZWB email to {} donors.").format(count),
                        level=messages.INFO,
                    )
                    return
                return response
        else:
            form = JZWBExportForm()

        opts = self.model._meta
        select_across = request.POST.get("select_across", "0") == "1"
        context = {
            "opts": opts,
            "queryset": queryset,
            "media": self.media,
            "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            "form": form,
            "select_across": select_across,
            "actionname": request.POST.get("action"),
            "applabel": opts.app_label,
        }

        return TemplateResponse(
            request, "admin/fds_donation/donor/export_jzwb.html", context
        )

    @admin.action(description=_("Detect recurring donations"))
    def detect_recurring_on_donor(self, request, queryset):
        """
        Detect recurrences in donations of donors.
        """
        from .services import detect_recurring_on_donor

        for donor in queryset:
            detect_recurring_on_donor(donor)

        self.message_user(
            request,
            _("Detecting recurrences on donors..."),
            level=messages.INFO,
        )

    def setup_mailing_messages(self, mailing, queryset):
        queryset = queryset.exclude(email="")

        count = queryset.count()
        MailingMessage.objects.bulk_create(
            [
                MailingMessage(mailing_id=mailing.id, donor_id=donor_id, email=email)
                for donor_id, email in queryset.values_list("id", "email")
            ]
        )

        return _("Prepared mailing of emailable donors with {count} recipients").format(
            count=count
        )

    def export_donor_csv(self, request, queryset):
        def get_donor_row(queryset):
            for donor in queryset:
                yield {
                    "id": donor.id,
                    "email": donor.email,
                    "first_name": donor.first_name,
                    "last_name": donor.last_name,
                    "company_name": donor.company_name,
                    "address": donor.address,
                    "postcode": donor.postcode,
                    "location": donor.city,
                    "country": donor.country.name,
                    "salutation": donor.get_salutation(),
                }

        donor_data = list(get_donor_row(queryset))
        return export_csv_response(dict_to_csv_stream(donor_data))


class DonationChangeList(ChangeList):
    def get_results(self, *args, **kwargs):
        ret = super().get_results(*args, **kwargs)
        agg = self.queryset.aggregate(
            amount_sum=Sum("amount"),
            amount_avg=Avg("amount"),
            amount_received_sum=Sum("amount_received"),
            donor_count=Count("donor_id", distinct=True),
            amount_median=median("amount"),
        )
        donor_agg = (
            Donor.objects.filter(donations__in=self.queryset)
            .distinct()
            .aggregate(recurring_donor_amount=Sum("recurring_amount"))
        )
        self.amount_sum = agg["amount_sum"]
        self.amount_avg = (
            round(agg["amount_avg"]) if agg["amount_avg"] is not None else "-"
        )
        self.amount_median = (
            round(agg["amount_median"]) if agg["amount_median"] is not None else "-"
        )
        self.amount_received_sum = agg["amount_received_sum"]
        self.donor_count = agg["donor_count"]
        self.recurring_donor_amount = donor_agg["recurring_donor_amount"]
        recurrence_agg = (
            Recurrence.objects.filter(donations__in=self.queryset)
            .distinct()
            .aggregate(
                recurring_count=Count("id"),
                cancel_count=Count("id", filter=Q(cancel_date__isnull=False)),
                monthly_amount=Sum(F("amount") / F("interval")),
                monthly_active_amount=Sum(
                    F("amount") / F("interval"), filter=Q(cancel_date__isnull=True)
                ),
            )
        )
        self.recurring_count = recurrence_agg["recurring_count"]
        self.cancel_count = recurrence_agg["cancel_count"]
        self.recurring_monthly_amount = (
            round(recurrence_agg["monthly_amount"])
            if recurrence_agg["monthly_amount"] is not None
            else "-"
        )
        self.recurring_monthly_active_amount = (
            round(recurrence_agg["monthly_active_amount"])
            if recurrence_agg["monthly_active_amount"] is not None
            else "-"
        )
        self.DONATION_PROJECTS = DONATION_PROJECTS
        return ret


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    def get_changelist(self, request):
        return DonationChangeList

    list_display = (
        "get_name",
        "timestamp",
        "amount",
        "completed",
        "received_timestamp",
        "get_number",
        "recurring",
        "project",
        "purpose",
        "method",
        "form_url",
        "reference",
        "keyword",
    )
    list_filter = (
        "completed",
        make_nullfilter("received_timestamp", _("Received")),
        make_daterangefilter("received_timestamp", _("Received timestamp")),
        "method",
        "project",
        "purpose",
        PassiveDonationListFilter,
        make_rangefilter("number", "Nr."),
        make_rangefilter("amount", _("amount")),
        make_daterangefilter("timestamp", _("Created timestamp")),
        "recurring",
        "first_recurring",
        "reference",
        make_nullfilter("export_date", _("Receipt exported")),
        make_nullfilter("receipt_date", _("Receipt sent")),
        ("donor", ForeignKeyFilter),
        ("recurrence", ForeignKeyFilter),
        make_nullfilter("payment", _("Has payment record")),
        "payment__status",
    )
    date_hierarchy = "timestamp"
    raw_id_fields = ("donor", "order", "payment")
    search_fields = (
        "donor__email",
        "donor__last_name",
        "donor__first_name",
        "donor__company_name",
        "keyword",
        "reference",
    )

    readonly_fields = (
        "timestamp",
        "completed",
        "received_timestamp",
        "amount_received",
        "email_sent",
        "number",
        "method",
        "recurring",
        "first_recurring",
        "recurrence",
        "form_url",
    )

    fieldsets = (
        (
            _("Donation"),
            {
                "fields": (
                    "donor",
                    "timestamp",
                    "amount",
                    "amount_received",
                    "received_timestamp",
                    "completed",
                    "method",
                )
            },
        ),
        (
            _("Analytics"),
            {
                "fields": (
                    "project",
                    "purpose",
                    "reference",
                    "keyword",
                    "number",
                    "form_url",
                    "recurring",
                    "first_recurring",
                    "recurrence",
                )
            },
        ),
        (
            _("Admin"),
            {
                "fields": (
                    "email_sent",
                    "note",
                    "receipt_date",
                    "export_date",
                )
            },
        ),
        (
            _("Payment"),
            {
                "fields": (
                    "order",
                    "payment",
                    "identifier",
                ),
                "classes": ("collapse", "collapse-closed"),
            },
        ),
        (
            _("Advanced"),
            {
                "fields": (
                    "data",
                    "extra_action_url",
                    "extra_action_label",
                ),
                "classes": ("collapse", "collapse-closed"),
            },
        ),
    )

    actions = [
        "resend_donation_mail",
        "send_donation_reminder",
        "tag_donors",
        "match_banktransfer",
        "clear_receipt_date",
        "tag_subscribers",
    ]

    tag_donors = make_batch_tag_action(
        action_name="tag_donors",
        autocomplete_url=DONOR_TAG_AUTOCOMPLETE,
        field=lambda obj, tags: obj.donor.tags.add(*tags),
        short_description="Füge Tag zu zugehörigen Spender:innen hinzu",
    )
    tag_subscribers = make_subscriber_tagger(
        lambda qs: (
            Donor.objects.exclude(email="")
            .filter(donations__in=qs)
            .distinct()
            .values_list("email", flat=True)
        )
    )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "export-csv/",
                self.admin_site.admin_view(self.export_csv),
                name="fds_donation-donation-export_csv",
            ),
            path(
                "import-banktransfers/",
                self.admin_site.admin_view(self.import_banktransfers),
                name="fds_donation-donation-import_banktransfers",
            ),
            path(
                "import-paypal/",
                self.admin_site.admin_view(self.import_paypal),
                name="fds_donation-donation-import_paypal",
            ),
        ]
        return my_urls + urls

    def get_name(self, obj):
        return str(obj.donor)

    get_name.short_description = "Name"
    get_name.admin_order_field = Concat(
        "donor__first_name", Value(" "), "donor__last_name"
    )

    def get_number(self, obj):
        return obj.number

    get_number.short_description = "Nr."
    get_number.admin_order_field = "number"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return self.enhance_queryset(qs)

    def enhance_queryset(self, qs):
        return qs.select_related("donor")

    def export_csv(self, request):
        def to_local(date):
            if date is None:
                return None
            return timezone.localtime(date).isoformat()

        def make_dicts(queryset):
            for donation in queryset.select_related("donor"):
                yield {
                    "id": donation.id,
                    "timestamp": to_local(donation.timestamp),
                    "amount": donation.amount,
                    "amount_received": donation.amount_received,
                    "received_timestamp": to_local(donation.received_timestamp),
                    "method": donation.method,
                    "purpose": donation.purpose,
                    "reference": donation.reference,
                    "keyword": donation.keyword,
                    "recurring": donation.recurring,
                    "first_recurring": donation.first_recurring,
                    "donor_id": donation.donor_id,
                    "number": donation.number,
                    "city": donation.donor.city,
                    "country": donation.donor.country,
                    "postcode": donation.donor.postcode,
                    "donor_recurring_amount": donation.donor.recurring_amount,
                    "first_donation": to_local(donation.donor.first_donation),
                    "last_donation": to_local(donation.donor.last_donation),
                    "subscribed": donation.donor.subscriber
                    and to_local(donation.donor.subscriber.subscribed),
                    "become_user": donation.donor.become_user,
                    "receipt": donation.donor.receipt,
                    "tags": ", ".join(x.name for x in donation.donor.tags.all()),
                    "donation_count": donation.donor.donations.all().count(),
                }

        response = self.changelist_view(request)
        try:
            queryset = response.context_data["cl"].queryset
        except (AttributeError, KeyError):
            return response

        return export_csv_response(dict_to_csv_stream(make_dicts(queryset)))

    export_csv.short_description = _("Export to CSV")

    def match_banktransfer(self, request, queryset):
        count = queryset.count()
        fail = False
        if count != 2:
            fail = True
        pending, received = queryset
        if received.received_timestamp is None:
            pending, received = received, pending
        if pending.received_timestamp or not received.received_timestamp:
            fail = True
        if pending.donor != received.donor:
            fail = True
        if pending.project != received.project:
            fail = True
        if pending.method != "banktransfer" or received.method != "banktransfer":
            fail = True
        if received.order or received.payment:
            fail = True
        if received.export_date or received.receipt_date:
            fail = True

        if fail:
            self.message_user(
                request,
                _("Need two banktransfer donations from same donor."),
                level=messages.WARNING,
            )
            return

        pending.amount_received = received.amount_received
        pending.amount = pending.amount_received
        pending.received_timestamp = received.received_timestamp
        pending.identifier = received.identifier
        received.delete()
        # Save after delete so donation number is updated correctly
        pending.save()
        self.message_user(request, _("Donations matched."), level=messages.INFO)

    match_banktransfer.short_description = _("Match planned to received banktransfer")

    def resend_donation_mail(self, request, queryset):
        from .services import send_donation_email

        resent = 0
        sent = 0
        for donation in queryset:
            if donation.email_sent:
                resent += 1
            donation.email_sent = None
            result = send_donation_email(donation)
            if result:
                sent += 1

        self.message_user(
            request,
            _("Send {sent} donation mails ({resent} resent).").format(
                sent=sent, resent=resent
            ),
            level=messages.INFO,
        )

    resend_donation_mail.short_description = _("Resend donation email")

    def clear_receipt_date(self, request, queryset):
        queryset.update(receipt_date=None)

    clear_receipt_date.short_description = _("Clear receipt date")

    def send_donation_reminder(self, request, queryset):
        from .services import send_donation_reminder_email

        sent = 0
        for donation in queryset:
            result = send_donation_reminder_email(donation)
            if result:
                sent += 1

        self.message_user(
            request,
            _("Send {sent} reminder mails.").format(sent=sent),
            level=messages.INFO,
        )

    send_donation_reminder.short_description = _("Send donation reminder")

    def import_banktransfers(self, request):
        from .tasks import import_banktransfers_task

        if not request.method == "POST":
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        xls_file_obj = request.FILES.get("file")
        project = request.POST["project"]
        if xls_file_obj is None:
            self.message_user(request, _("No file provided."), level=messages.ERROR)
            return redirect("admin:fds_donation_donation_changelist")

        # Create a named temporary file for background task to read
        file_obj = tempfile.NamedTemporaryFile(delete=False)
        file_obj.write(xls_file_obj.read())
        file_obj.close()

        import_banktransfers_task.delay(file_obj.name, project, user_id=request.user.id)

        self.message_user(
            request,
            _("Import will start in background."),
            level=messages.INFO,
        )

        return redirect("admin:fds_donation_donation_changelist")

    def import_paypal(self, request):
        from .tasks import import_paypal_task

        if not request.method == "POST":
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        csv_file = request.FILES.get("file")
        if csv_file is None:
            self.message_user(request, _("No file provided."), level=messages.ERROR)
            return redirect("admin:fds_donation_donation_changelist")

        # Create a named temporary file for background task to read
        file_obj = tempfile.NamedTemporaryFile(delete=False)
        file_obj.write(csv_file.read())
        file_obj.close()

        import_paypal_task.delay(file_obj.name, user_id=request.user.id)

        self.message_user(
            request,
            _("Import will start in background."),
            level=messages.INFO,
        )

        return redirect("admin:fds_donation_donation_changelist")


@admin.register(DonationGift)
class DonationGiftAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "category_slug",
        "inventory",
        "order_count",
        "remaining_count",
    )
    list_filter = ("category_slug",)
    search_fields = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            order_count=Count("donationgiftorder"),
        )

    def order_count(self, obj):
        return obj.order_count

    order_count.admin_order_field = "order_count"
    order_count.short_description = _("order count")

    def remaining_count(self, obj):
        if obj.inventory is None:
            return "-"
        return obj.inventory - obj.order_count

    remaining_count.short_description = _("remaining count")


@admin.register(DonationGiftOrder)
class DonationGiftOrderAdmin(admin.ModelAdmin):
    date_hierarchy = "timestamp"
    raw_id_fields = ("donation",)
    list_display = (
        "donation_gift",
        "email",
        "timestamp",
        "donation_received",
        "donation_amount",
        "donation_amount_received",
        "recurring_amount",
        "shipped",
    )
    list_filter = (
        make_nullfilter("donation__received_timestamp", _("donation received")),
        make_nullfilter("shipped", _("has shipped")),
        make_daterangefilter("timestamp", _("order timestamp")),
        "donation_gift",
    )
    search_fields = ("email", "donation__donor__email", "donation_gift__name")
    actions = ["notify_shipped", "set_shipped", "export_csv"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("donation", "donation__donor", "donation_gift")
        )

    def donation_amount(self, obj):
        if obj.donation:
            return obj.donation.amount
        return None

    donation_amount.short_description = _("donation amount")

    def donation_amount_received(self, obj):
        if obj.donation:
            return obj.donation.amount_received
        return None

    donation_amount_received.short_description = _("donation amount received")

    def donation_received(self, obj):
        if obj.donation:
            return obj.donation.received_timestamp
        return None

    donation_received.short_description = _("donation received date")

    def recurring_amount(self, obj):
        if obj.donation:
            return obj.donation.donor.recurring_amount
        return None

    recurring_amount.short_description = _("recurring amount")

    def notify_shipped(self, request, queryset):
        queryset = queryset.filter(shipped=None)
        count = len(queryset)
        now = timezone.now()
        for gift_order in queryset:
            send_donation_gift_order_shipped(gift_order)
        queryset.update(shipped=now)
        self.message_user(
            request,
            _("Send {count} shipped mails.").format(count=count),
            level=messages.INFO,
        )

    notify_shipped.short_description = _("Send shipped email and set date")

    def set_shipped(self, request, queryset):
        queryset = queryset.filter(shipped=None)
        count = len(queryset)
        queryset.update(shipped=timezone.now())
        self.message_user(
            request,
            _("Set {count} order to shipped.").format(count=count),
            level=messages.INFO,
        )

    set_shipped.short_description = _("Set shipped date")

    def export_csv(self, request, queryset):
        def get_rows(queryset):
            for object in queryset:
                yield {
                    "id": object.id,
                    "email": object.email,
                    "first_name": object.first_name,
                    "last_name": object.last_name,
                    "company_name": object.company_name,
                    "address": object.address,
                    "postcode": object.postcode,
                    "city": object.city,
                    "country": object.country.name,
                    "full_address": object.formatted_address(),
                }

        donor_data = list(get_rows(queryset))
        return export_csv_response(dict_to_csv_stream(donor_data))

    export_csv.short_description = _("export as csv")


@admin.register(DefaultDonation)
class DefaultDonationAdmin(DonationAdmin):
    list_display = [x for x in DonationAdmin.list_display if x != "project"]
    list_filter = [x for x in DonationAdmin.list_filter if x != "project"]


class DeferredDonationAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "amount",
        "donor_details",
        "number",
        "admin_link_donations",
        "donor_email_confirmed",
        "payment_fraud_message",
        "payment_details",
        "project",
        "purpose",
        "method",
        "reference",
        "keyword",
    )
    raw_id_fields = ("donor", "order", "payment")

    actions = ["confirm", "cancel"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(payment__status=PaymentStatus.DEFERRED)
            .select_related("payment", "donor")
        )

    def admin_link_donations(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:fds_donation_donation_changelist")
            + ("?donor=%s" % obj.donor_id),
            _("donations"),
        )

    admin_link_donations.short_description = _("donations")

    def donor_details(self, obj):
        return str(obj.donor)

    donor_details.short_description = _("Donor")
    donor_details.admin_order_field = Concat(
        "donor__first_name", Value(" "), "donor__last_name"
    )

    def donor_email_confirmed(self, obj):
        return obj.donor.email_confirmed

    donor_email_confirmed.short_description = _("Email confirmed")

    def payment_fraud_message(self, obj):
        return obj.payment.fraud_message

    payment_fraud_message.short_description = _("Suspicious")

    def payment_fraud_message(self, obj):
        return obj.payment.fraud_message

    payment_fraud_message.short_description = _("Suspicious")

    def payment_details(self, obj):
        try:
            iban = obj.payment.attrs.iban
        except AttributeError:
            iban = "n/a"
        iban = iban[:4]
        return "IBAN[4]: {iban}, IP: {ip}".format(
            iban=iban,
            ip=obj.payment.customer_ip_address,
        )

    payment_details.short_description = _("Payment details")

    @admin.action(description=_("✅ Confirm donations"))
    def confirm(self, request, queryset):
        for donation in queryset:
            obj = donation.payment
            provider = obj.get_provider()
            provider.confirm_payment(obj)

    @admin.action(description=_("❌ Cancel donations"))
    def cancel(self, request, queryset):
        for donation in queryset:
            obj = donation.payment
            provider = obj.get_provider()
            provider.cancel_payment(obj)


admin.site.register(DeferredDonation, DeferredDonationAdmin)


@admin.register(DonationFormCMSPlugin)
class DonationFormAdmin(admin.ModelAdmin):
    list_display = (
        "get_title",
        "language",
        "interval",
        "amount_presets",
        "collapsed",
        "purpose",
        "link",
    )

    def get_title(self, obj):
        return obj.title or "-"

    def get_queryset(self, request):
        from django.contrib.contenttypes.models import ContentType

        from cms.models import PageContent, Placeholder
        from djangocms_versioning.constants import PUBLISHED
        from djangocms_versioning.models import Version

        ct = ContentType.objects.get_for_model(PageContent)
        published_page_content = PageContent.objects.filter(
            pk__in=Version.objects.filter(
                content_type=ct,
                state=PUBLISHED,
            ).values("object_id"),
            language=request.LANGUAGE_CODE,
        )
        placeholders = Placeholder.objects.filter(
            content_type=ct, object_id__in=published_page_content
        )

        return super().get_queryset(request).filter(placeholder__in=placeholders)

    def link(self, obj):
        url = self.view_on_site(obj)
        if url:
            return format_html('<a href="{}" target="_blank">{}</a>', url, url)
        return _("Not available")

    def view_on_site(self, obj):
        try:
            return obj.placeholder.page.get_absolute_url()
        except AttributeError:
            return False


@admin.register(DonationFormViewCount)
class DonationFormViewCountAdmin(admin.ModelAdmin):
    list_display = (
        "path",
        "reference",
        "date",
        "count",
        "last_updated",
    )
    search_fields = (
        "path",
        "reference",
    )
    date_hierarchy = "date"


@admin.register(Recurrence)
class RecurrenceAdmin(admin.ModelAdmin):
    list_display = (
        "donor",
        "project",
        "method",
        "start_date",
        "active",
        "interval",
        "amount",
        "cancel_date",
        "days",
        "sum_amount",
    )
    date_hierarchy = "start_date"
    list_filter = (
        "project",
        "cancel_date",
        "method",
        "interval",
        ("donor", ForeignKeyFilter),
    )
    search_fields = ("donor__email",)
    raw_id_fields = (
        "subscription",
        "donor",
    )
    readonly_fields = (
        "donor",
        "subscription",
        "active",
        "project",
        "method",
        "start_date",
        "interval",
        "amount",
        "sum_amount",
        "days",
    )
    fieldsets = (
        (
            _("Recurrence"),
            {
                "fields": (
                    "donor",
                    "subscription",
                    "project",
                    "method",
                    "start_date",
                    "active",
                    "interval",
                    "amount",
                    "sum_amount",
                    "days",
                )
            },
        ),
        (
            _("Cancellation"),
            {
                "fields": (
                    "cancel_date",
                    "cancel_reason",
                    "cancel_feedback",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("subscription", "donor")
            .prefetch_related("donations")
        )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.cancel_date:
            return self.readonly_fields + ("cancel_date",)
        if obj and obj.method == "banktransfer":
            return self.readonly_fields
        return self.readonly_fields + (
            "cancel_date",
            "cancel_reason",
            "cancel_feedback",
        )

    def sum_amount(self, obj):
        return obj.sum_amount()

    def days(self, obj):
        return obj.days()
