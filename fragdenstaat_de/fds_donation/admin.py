from collections import Counter
from io import BytesIO
import uuid
import zipfile

from django.db.models import Q, Sum, Avg, Count, Value, Aggregate, F
from django.db.models.functions import Concat
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import admin, messages
from django.conf.urls import url
from django.urls import reverse
from django.contrib.admin.views.main import ChangeList
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.text import slugify
from django.utils.html import format_html
from django.contrib.admin import helpers
from django.template.response import TemplateResponse

from froide.helper.admin_utils import (
    ForeignKeyFilter, make_nullfilter, AdminTagAllMixIn,
)
from froide.helper.csv_utils import dict_to_csv_stream, export_csv_response

from fragdenstaat_de.fds_mailing.utils import SetupMailingMixin
from fragdenstaat_de.fds_mailing.models import MailingMessage

from .models import DonationGift, Donor, Donation
from .external import import_banktransfers, import_paypal
from .filters import DateRangeFilter, make_rangefilter
from .services import send_donation_email
from .forms import get_merge_donor_form
from .utils import (
    propose_donor_merge, merge_donors,
    get_donation_pivot_data_and_config
)
from .export import get_zwbs, ZWBPDFGenerator


def median(field):
    return Aggregate(
        F(field),
        function="percentile_cont",
        template="%(function)s(0.5) WITHIN GROUP (ORDER BY %(expressions)s)",
    )


class DonorChangeList(ChangeList):
    def get_results(self, *args, **kwargs):
        ret = super().get_results(*args, **kwargs)
        q = self.queryset.aggregate(
            amount_total_sum=Sum('amount_total'),
            amount_last_year_sum=Sum('amount_last_year'),
            amount_total_median=median('amount_total'),
            amount_total_avg=Avg('amount_total'),
            amount_last_year_avg=Avg('amount_last_year')
        )
        self.amount_total_sum = q['amount_total_sum']
        self.amount_total_avg = round(q['amount_total_avg']) if q['amount_total_avg'] is not None else '-'
        self.amount_last_year_sum = q['amount_last_year_sum']
        self.amount_last_year_avg = round(q['amount_last_year_avg']) if q['amount_last_year_avg'] is not None else '-'
        self.amount_total_median = round(q['amount_total_median'])
        return ret


class DonorAdmin(SetupMailingMixin, AdminTagAllMixIn, admin.ModelAdmin):
    list_display = (
        'get_name', 'admin_link_donations', 'city',
        'active',
        'last_donation',
        'amount_total',
        'amount_last_year',
        'recurring_amount',
        'receipt',
    )
    list_filter = (
        'active',
        make_nullfilter('subscription', _('Dauerspende')),
        make_rangefilter('amount_last_year', _('amount last year')),
        make_rangefilter('recurring_amount', _('recurring monthly amount')),
        'email_confirmed', 'contact_allowed',
        'become_user',
        'receipt',
        'invalid',
        make_nullfilter('duplicate', _('has duplicate')),
        make_nullfilter('user_id', _('has user')),
        ('user', ForeignKeyFilter),
        'tags',
    )
    date_hierarchy = 'first_donation'
    search_fields = (
        'email', 'last_name', 'first_name', 'company_name',
        'identifier', 'note'
    )
    raw_id_fields = ('user', 'subscription')
    tag_all_config = ('tags', None)
    actions = [
        'merge_donors', 'detect_duplicates', 'clear_duplicates',
        'export_zwbs', 'get_zwb_pdf', 'tag_all',
        'send_mailing'
    ] + SetupMailingMixin.actions

    def get_changelist(self, request):
        return DonorChangeList

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        donations_filter = Q(donations__received=True)
        last_year = timezone.now().year - 1
        qs = qs.annotate(
            amount_total=Sum('donations__amount', filter=donations_filter),
            amount_last_year=Sum(
                'donations__amount',
                filter=donations_filter & Q(
                    donations__received_timestamp__year=last_year
                )
            )
        )
        return qs

    def amount_total(self, obj):
        return obj.amount_total
    amount_total.admin_order_field = 'amount_total'

    def amount_last_year(self, obj):
        return obj.amount_last_year
    amount_last_year.admin_order_field = 'amount_last_year'

    def get_name(self, obj):
        return str(obj)
    get_name.short_description = 'Name'
    get_name.admin_order_field = Concat('first_name', Value(' '), 'last_name')

    def admin_link_donations(self, obj):
        return format_html('<a href="{}">{}</a>',
            reverse('admin:fds_donation_donation_changelist') + (
                '?donor=%s' % obj.pk), _('donations'))
    admin_link_donations.short_description = _('donations')

    def clear_duplicates(self, request, queryset):
        queryset.update(duplicate=None)
        self.message_user(request, _('Duplicate flags cleared.'))
    clear_duplicates.short_description = _("Clear duplicate flag on donors")

    def detect_duplicates(self, request, queryset):
        from collections import defaultdict

        emails = defaultdict(list)
        full_names = defaultdict(list)
        id_sets = defaultdict(set)

        for obj in queryset:
            if obj.email:
                emails[obj.email].append(obj.id)
            full_names[obj.get_full_name()].append(obj.id)

        for ddict in (emails, full_names):
            for k, id_list in ddict.items():
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
        self.message_user(request, _('Detected {dup} duplicate sets with {donors} donors').format(
            dup=count, donors=len(already)
        ))

    detect_duplicates.short_description = _("Detect duplicate donors")

    def merge_donors(self, request, queryset):
        """
        Send mail to users

        """

        select_across = request.POST.get('select_across', '0') == '1'
        if select_across:
            self.message_user(request, _('Select across not allowed!'))
            return

        candidates = queryset.order_by('-id')
        candidate_ids = [x.id for x in candidates]
        if len(candidate_ids) < 2:
            self.message_user(request, _('Need to select more than one!'))
            return
        subs = Counter()
        for c in candidates:
            if c.subscription_id:
                subs[c.subscription_id] += 1
        if len(subs) > 1:
            self.message_user(request, _('Two different subscriptions detected!'))
            return

        MergeDonorForm = get_merge_donor_form(self.admin_site)

        donor_form = None
        if 'salutation' in request.POST:
            donor_form = MergeDonorForm(data=request.POST)
            if donor_form.is_valid():
                primary_id = None
                if request.POST.get('primary') is not None:
                    primary_id = request.POST['primary']
                    if primary_id not in candidate_ids:
                        primary_id = None
                if primary_id is None:
                    primary_id = candidate_ids[0]

                donor = merge_donors(candidates, primary_id, donor_form.cleaned_data)

                self.message_user(request, _('Merged {count} donors into {donor}').format(
                    count=len(candidates), donor=donor
                ))
                return None

        if donor_form is None:
            merged_donor = propose_donor_merge(candidates, MergeDonorForm.Meta.fields)
            donor_form = MergeDonorForm(instance=merged_donor)

        context = {
            'opts': self.model._meta,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'queryset': candidates,
            'form': donor_form,
        }

        # Display the confirmation page
        return TemplateResponse(request, 'admin/fds_donation/donor/merge_donors.html',
            context)
    merge_donors.short_description = _("Merge donors")

    def get_zwb_pdf(self, request, queryset):
        if queryset.count() == 1:
            donor = queryset[0]
            pdf_generator = ZWBPDFGenerator(donor)
            response = HttpResponse(
                pdf_generator.get_pdf_bytes(),
                content_type='application/pdf'
            )
            filename = '%s_%s.pdf' % (
                slugify(donor.get_order_name()), donor.id
            )
            response['Content-Disposition'] = 'attachment; filename="%s"' % filename
            return response

        zfile_obj = BytesIO()
        zfile = zipfile.ZipFile(zfile_obj, 'w')
        for donor in queryset:
            pdf_generator = ZWBPDFGenerator(donor)
            filename = '%s_%s.pdf' % (
                slugify(donor.get_order_name()), donor.id
            )
            zfile.writestr(filename, pdf_generator.get_pdf_bytes())
        zfile.close()

        response = HttpResponse(
            zfile_obj.getvalue(),
            content_type='application/zip'
        )
        response['Content-Disposition'] = 'attachment; filename="zwbs_%s.zip"' % (timezone.now().isoformat())
        return response
    get_zwb_pdf.short_description = _("Generate ZWB PDFs")

    def export_zwbs(self, request, queryset):
        # Filter by ZWB criteria
        # Only valid records
        queryset = queryset.filter(invalid=False)

        # Last year received donations that have not yet been ZWBed
        last_year = timezone.now().year - 1
        donations_filter = Q(
            donations__received=True,
            donations__receipt_date__isnull=True,
            donations__received_timestamp__year=last_year
        )

        queryset = queryset.annotate(
            amount_last_year=Sum(
                'donations__amount',
                filter=donations_filter
            )
        )

        # Only (with receipt AND > 25) OR (> 50)
        queryset = queryset.filter(
            Q(receipt=True, amount_last_year__gte=25) |
            Q(amount_last_year__gte=50)
        )

        queryset = queryset.order_by('last_name', 'first_name')

        return export_csv_response(
            dict_to_csv_stream(get_zwbs(queryset, year=last_year))
        )
    export_zwbs.short_description = _("Export ZWB mail merge data")

    def setup_mailing_messages(self, mailing, queryset):
        queryset = queryset.exclude(email='')

        count = queryset.count()
        MailingMessage.objects.bulk_create([
            MailingMessage(
                mailing_id=mailing.id,
                donor_id=donor_id
            )
            for donor_id in queryset.values_list('id', flat=True)
        ])

        return _(
            'Prepared mailing of emailable donors'
            'with {count} recipients').format(
                count=count
        )


class DonationChangeList(ChangeList):
    def get_results(self, *args, **kwargs):
        ret = super().get_results(*args, **kwargs)
        q = self.queryset.aggregate(
            amount_sum=Sum('amount'),
            amount_avg=Avg('amount'),
            amount_received_sum=Sum('amount_received'),
            donor_count=Count('donor_id', distinct=True),
            amount_median=median('amount')
        )
        self.amount_sum = q['amount_sum']
        self.amount_avg = round(q['amount_avg']) if q['amount_avg'] is not None else '-'
        self.amount_median = round(q['amount_median'])
        self.amount_received_sum = q['amount_received_sum']
        self.donor_count = q['donor_count']
        return ret


class DonationAdmin(admin.ModelAdmin):
    def get_changelist(self, request):
        return DonationChangeList

    list_display = (
        'get_name', 'timestamp', 'amount', 'completed', 'received',
        'purpose',
        'reference', 'keyword', 'method', 'recurring',
    )
    list_filter = (
        'completed', 'received',
        ('timestamp', DateRangeFilter),
        'method',
        'purpose',
        'recurring',
        'reference',
        make_nullfilter('export_date', _('Receipt exported')),
        make_nullfilter('receipt_date', _('Receipt sent')),
        ('donor', ForeignKeyFilter),
    )
    date_hierarchy = 'timestamp'
    raw_id_fields = ('donor', 'order', 'payment')
    search_fields = (
        'donor__email', 'donor__last_name', 'donor__first_name',
        'donor__company_name',
    )

    actions = ['resend_donation_mail']

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            url(r'^pivot/$',
                self.admin_site.admin_view(self.show_pivot),
                name='fds_donation-donation-show_pivot'),
            url(r'^import-banktransfers/$',
                self.admin_site.admin_view(self.import_banktransfers),
                name='fds_donation-donation-import_banktransfers'),
            url(r'^import-paypal/$',
                self.admin_site.admin_view(self.import_paypal),
                name='fds_donation-donation-import_paypal'),
        ]
        return my_urls + urls

    def get_name(self, obj):
        return str(obj.donor)
    get_name.short_description = 'Name'
    get_name.admin_order_field = Concat('donor__first_name', Value(' '), 'donor__last_name')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('donor')

    def show_pivot(self, request):
        response = self.changelist_view(request)
        try:
            queryset = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        opts = self.model._meta
        data, config = get_donation_pivot_data_and_config(queryset)
        ctx = {
            'app_label': opts.app_label,
            'opts': opts,
            'pivot_data': data,
            'pivot_config': config,
        }
        return render(request, "pivot/admin_pivot.html", ctx)

    def resend_donation_mail(self, request, queryset):
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
            request, _('Send {sent} donation mails ({resent} resent).').format(
                sent=sent, resent=resent
            ),
            level=messages.INFO
        )
    resend_donation_mail.short_description = _('Resend donation email')

    def import_banktransfers(self, request):
        if not request.method == 'POST':
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        xls_file = request.FILES.get('file')
        if xls_file is None:
            self.message_user(
                request, _('No file provided.'), level=messages.ERROR
            )
            return redirect('admin:fds_donation_donation_changelist')

        xls_file = BytesIO(xls_file.read())

        count, new_count = import_banktransfers(xls_file)

        self.message_user(
            request, _('Imported {rows} rows, {new} new rows.').format(
                rows=count, new=new_count
            ),
            level=messages.INFO
        )

        return redirect('admin:fds_donation_donation_changelist')

    def import_paypal(self, request):
        if not request.method == 'POST':
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        csv_file = request.FILES.get('file')
        if csv_file is None:
            self.message_user(
                request, _('No file provided.'), level=messages.ERROR
            )
            return redirect('admin:fds_donation_donation_changelist')

        csv_file = BytesIO(csv_file.read())

        count, new_count = import_paypal(csv_file)

        self.message_user(
            request, _('Imported {rows} rows, {new} new rows.').format(
                rows=count, new=new_count
            ),
            level=messages.INFO
        )

        return redirect('admin:fds_donation_donation_changelist')


class DonationGiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_slug')
    list_filter = ('category_slug',)
    search_fields = ('name',)


admin.site.register(Donor, DonorAdmin)
admin.site.register(Donation, DonationAdmin)
admin.site.register(DonationGift, DonationGiftAdmin)
