import uuid
from collections import defaultdict
from io import BytesIO

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.filters import SimpleListFilter
from django.contrib.admin.views.main import ChangeList
from django.core.exceptions import PermissionDenied
from django.db.models import Aggregate, Avg, Count, F, Max, Q, Sum, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from adminsortable2.admin import SortableAdminMixin
from fragdenstaat_de.fds_mailing.models import MailingMessage
from fragdenstaat_de.fds_mailing.utils import SetupMailingMixin

from froide.helper.admin_utils import (
    ForeignKeyFilter,
    MultiFilterMixin,
    TaggitListFilter,
    make_batch_tag_action,
    make_daterangefilter,
    make_emptyfilter,
    make_nullfilter,
    make_rangefilter,
)
from froide.helper.csv_utils import dict_to_csv_stream, export_csv_response
from froide.helper.widgets import TagAutocompleteWidget

from .export import JZWBExportForm
from .models import (
    DONATION_PROJECTS,
    DefaultDonation,
    Donation,
    DonationGift,
    DonationGiftOrder,
    Donor,
    DonorTag,
    TaggedDonor,
)
from .services import send_donation_gift_order_shipped


def median(field):
    return Aggregate(
        F(field),
        function="percentile_cont",
        template="%(function)s(0.5) WITHIN GROUP (ORDER BY %(expressions)s)",
    )


DONOR_TAG_AUTOCOMPLETE = reverse_lazy("admin:fds_donation-donortag-autocomplete")


class DonorTagAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "autocomplete/",
                self.admin_site.admin_view(self.autocomplete),
                name="fds_donation-donortag-autocomplete",
            ),
        ]
        return my_urls + urls

    def autocomplete(self, request):
        if not request.method == "GET":
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        query = request.GET.get("q", "")
        tags = []
        if query:
            tags = DonorTag.objects.filter(name__istartswith=query).values_list(
                "name", flat=True
            )
        return JsonResponse(
            {"objects": [{"value": t, "label": t} for t in tags]}, safe=False
        )


class DonorProjectFilter(MultiFilterMixin, SimpleListFilter):
    title = "Project"
    parameter_name = "donations__project"
    lookup_name = "__in"

    def queryset(self, request, queryset):
        """
        don't filter donors on donation projects here,
        but in Admin.get_queryset().
        This avoids double counting donations that are
        annotated in get_queryset()
        """
        return queryset

    def lookups(self, request, model_admin):
        return DONATION_PROJECTS


class DonorTagListFilter(MultiFilterMixin, TaggitListFilter):
    tag_class = TaggedDonor
    title = "Tags"
    parameter_name = "tags__slug"
    lookup_name = "__in"


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
        q = self.queryset.aggregate(
            amount_total_sum=Sum("amount_total"),
            amount_last_year_sum=Sum("amount_last_year"),
            amount_total_median=median("amount_total"),
            amount_total_avg=Avg("amount_total"),
            amount_last_year_avg=Avg("amount_last_year"),
            recurring_total=Sum("recurring_amount"),
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
        return ret


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
        make_nullfilter("subscriptions", _("Dauerspende")),
        make_rangefilter("amount_last_year", _("amount last year")),
        make_rangefilter("recurring_amount", _("recurring monthly amount")),
        make_daterangefilter("last_donation", _("Last donation")),
        "subscriber__subscribed",
        "email_confirmed",
        "become_user",
        "receipt",
        "invalid",
        DonorProjectFilter,
        make_emptyfilter("email", _("has email")),
        make_nullfilter("duplicate", _("has duplicate")),
        make_nullfilter("user_id", _("has user")),
        ("user", ForeignKeyFilter),
        DonorTagListFilter,
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
    actions = [
        "send_donor_optin_email",
        "merge_donors",
        "detect_duplicates",
        "clear_duplicates",
        "export_jzwb",
        "tag_all",
        "mark_invalid_addresses",
        "send_mailing",
        "update_newsletter_tag",
        "export_donor_csv",
    ] + SetupMailingMixin.actions

    tag_all = make_batch_tag_action(autocomplete_url=DONOR_TAG_AUTOCOMPLETE)

    def get_changelist(self, request):
        return DonorChangeList

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
            **any_donation
        )
        if donation_projects:
            qs = qs.filter(any_donation__gt=0)
        return qs

    def donation_count(self, obj):
        return obj.donation_count

    donation_count.admin_order_field = "donation_count"
    donation_count.short_description = "Anzahl"

    def amount_total(self, obj):
        return obj.amount_total

    amount_total.admin_order_field = "amount_total"

    def amount_last_year(self, obj):
        return obj.amount_last_year

    amount_last_year.admin_order_field = "amount_last_year"

    def last_donation(self, obj):
        return obj.last_donation

    last_donation.admin_order_field = "last_donation"
    last_donation.short_description = "Letzte Spende"

    def get_name(self, obj):
        return str(obj)

    get_name.short_description = "Name"
    get_name.admin_order_field = Concat("first_name", Value(" "), "last_name")

    def admin_link_donations(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            reverse("admin:fds_donation_donation_changelist") + ("?donor=%s" % obj.pk),
            _("donations"),
        )

    admin_link_donations.short_description = _("donations")

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

    send_donor_optin_email.short_description = _("Send opt-in mail")

    def clear_duplicates(self, request, queryset):
        queryset.update(duplicate=None)
        self.message_user(request, _("Duplicate flags cleared."))

    clear_duplicates.short_description = _("Clear duplicate flag on donors")

    def detect_duplicates(self, request, queryset):
        emails = defaultdict(list)
        full_names = defaultdict(list)
        id_sets = defaultdict(set)

        for obj in queryset:
            if obj.email:
                emails[obj.email].append(obj.id)
            full_names[obj.get_full_name()].append(obj.id)

        for ddict in (emails, full_names):
            for id_list in ddict.values():
                if len(id_list) > 1:
                    id_set = set()
                    for x in id_list:
                        if x in id_sets:
                            id_set.update(id_sets[x])
                        id_set.add(x)
                        id_sets[x] = id_set
        already = set()
        count = 0
        for key, id_set in id_sets.items():
            if key in already:
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

    detect_duplicates.short_description = _("Detect duplicate donors")

    @admin.action(description=_("Mark invalid addresses"))
    def mark_invalid_addresses(self, request, queryset):
        queryset.filter(
            Q(postcode="")
            | Q(address="")
            | Q(city="")
            | Q(last_name="")
            | ~(Q(postcode__regex=r"^\d{5}$") | ~Q(country="DE"))
        ).update(invalid=True)

    def merge_donors(self, request, queryset):
        """
        Send mail to users

        """
        from .forms import get_merge_donor_form
        from .utils import merge_donors, propose_donor_merge

        select_across = request.POST.get("select_across", "0") == "1"
        if select_across:
            self.message_user(request, _("Select across not allowed!"))
            return

        candidates = queryset.order_by("-id")
        candidate_ids = [x.id for x in candidates]
        if len(candidate_ids) < 2:
            self.message_user(request, _("Need to select more than one!"))
            return

        MergeDonorForm = get_merge_donor_form(self.admin_site)

        donor_form = None
        if "salutation" in request.POST:
            donor_form = MergeDonorForm(data=request.POST)
            if donor_form.is_valid():
                primary_id = None
                if request.POST.get("primary") is not None:
                    primary_id = request.POST["primary"]
                    if primary_id not in candidate_ids:
                        primary_id = None
                if primary_id is None:
                    primary_id = candidate_ids[0]

                donor = merge_donors(candidates, primary_id, donor_form.cleaned_data)

                self.message_user(
                    request,
                    _("Merged {count} donors into {donor}").format(
                        count=len(candidates), donor=donor
                    ),
                )
                return None

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

    merge_donors.short_description = _("Merge donors")

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

    def setup_mailing_messages(self, mailing, queryset):
        queryset = queryset.exclude(email="")

        count = queryset.count()
        MailingMessage.objects.bulk_create(
            [
                MailingMessage(mailing_id=mailing.id, donor_id=donor_id)
                for donor_id in queryset.values_list("id", flat=True)
            ]
        )

        return _(
            "Prepared mailing of emailable donors " "with {count} recipients"
        ).format(count=count)

    def export_donor_csv(self, request, queryset):
        def get_donor_row(queryset):
            for donor in queryset:
                yield {
                    "id": donor.id,
                    "email": donor.email,
                    "first_name": donor.first_name,
                    "last_name": donor.last_name,
                    "address": donor.address,
                    "postcode": donor.postcode,
                    "location": donor.city,
                    "country": donor.country.name,
                    "salutation": donor.get_salutation_display(),
                }

        donor_data = list(get_donor_row(queryset))
        return export_csv_response(dict_to_csv_stream(donor_data))


class PassiveDonationListFilter(admin.SimpleListFilter):
    title = _("Passive donation")
    parameter_name = "is_passive"

    def lookups(self, request, model_admin):
        return (
            ("0", _("active")),
            ("1", _("passive")),
        )

    def queryset(self, request, queryset):
        active_condition = Q(recurring=False) | Q(first_recurring=True)
        if self.value() == "0":
            return queryset.filter(active_condition)
        elif self.value() == "1":
            return queryset.filter(~active_condition)
        return queryset


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

        self.DONATION_PROJECTS = DONATION_PROJECTS
        return ret


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

    actions = [
        "resend_donation_mail",
        "send_donation_reminder",
        "tag_donors",
        "match_banktransfer",
        "clear_receipt_date",
    ]

    tag_donors = make_batch_tag_action(
        action_name="tag_donors",
        autocomplete_url=DONOR_TAG_AUTOCOMPLETE,
        field=lambda obj, tags: obj.donor.tags.add(*tags),
        short_description="Füge Tag zu zugehörigen Spender:innen hinzu",
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
        from .external import import_banktransfers

        if not request.method == "POST":
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        xls_file_obj = request.FILES.get("file")
        project = request.POST["project"]
        if xls_file_obj is None:
            self.message_user(request, _("No file provided."), level=messages.ERROR)
            return redirect("admin:fds_donation_donation_changelist")

        xls_file = BytesIO(xls_file_obj.read())
        xls_file.name = xls_file_obj.name

        count, new_count = import_banktransfers(xls_file, project)

        self.message_user(
            request,
            _("Imported {rows} rows, {new} new rows.").format(
                rows=count, new=new_count
            ),
            level=messages.INFO,
        )

        return redirect("admin:fds_donation_donation_changelist")

    def import_paypal(self, request):
        from .external import import_paypal

        if not request.method == "POST":
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        csv_file = request.FILES.get("file")
        if csv_file is None:
            self.message_user(request, _("No file provided."), level=messages.ERROR)
            return redirect("admin:fds_donation_donation_changelist")

        csv_file = BytesIO(csv_file.read())

        count, new_count = import_paypal(csv_file)

        self.message_user(
            request,
            _("Imported {rows} rows, {new} new rows.").format(
                rows=count, new=new_count
            ),
            level=messages.INFO,
        )

        return redirect("admin:fds_donation_donation_changelist")


class DonationGiftAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ("name", "category_slug")
    list_filter = ("category_slug",)
    search_fields = ("name",)


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
        "donation_gift",
    )
    search_fields = ("email", "donation__donor__email", "donation_gift__name")
    actions = ["notify_shipped"]

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

    notify_shipped.short_description = _("notify shipped and set date")


class DefaultDonationAdmin(DonationAdmin):
    list_display = [x for x in DonationAdmin.list_display if x != "project"]
    list_filter = [x for x in DonationAdmin.list_filter if x != "project"]


admin.site.register(Donor, DonorAdmin)
admin.site.register(Donation, DonationAdmin)
admin.site.register(DonationGift, DonationGiftAdmin)
admin.site.register(DonationGiftOrder, DonationGiftOrderAdmin)
admin.site.register(DonorTag, DonorTagAdmin)
admin.site.register(DefaultDonation, DefaultDonationAdmin)
