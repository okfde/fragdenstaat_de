from django.contrib import admin
from django.db.models import Q, Count
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from froide.helper.csv_utils import export_csv, export_csv_response

from fragdenstaat_de.fds_mailing.utils import SetupMailingMixin

from .models import Newsletter, Subscriber


class NewsletterAdmin(SetupMailingMixin, admin.ModelAdmin):
    list_display = (
        'title', 'visible', 'subscriber_count', 'admin_subscribers'
    )
    prepopulated_fields = {'slug': ('title',)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            subscriber_count=Count(
                'subscribers', filter=Q(subscribers__subscribed__isnull=False)
            )
        )
        return qs

    def subscriber_count(self, obj):
        return obj.subscriber_count
    subscriber_count.admin_order_field = 'subscriber_count'
    subscriber_count.short_description = _('active subscriber count')

    def admin_subscribers(self, obj):
        url = reverse(
            'admin:fds_newsletter_subscriber_changelist',
            current_app=self.admin_site.name
        )

        return format_html(
            '<a href="{}?newsletter__id__exact={}">{}</a>', url, obj.id,
            _('See all subscribers')
        )
    admin_subscribers.short_description = ''


class SubscriberAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = (
        'admin_email', 'newsletter', 'subscribed',
        'unsubscribed',
    )
    list_filter = (
        'newsletter', 'subscribed', 'unsubscribed',
    )
    search_fields = (
        'email', 'user__email'
    )
    readonly_fields = (
        'created', 'activation_code'
    )
    date_hierarchy = 'created'
    actions = ['export_subscribers_csv']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('newsletter')
        qs = qs.prefetch_related('user')
        return qs

    def admin_email(self, obj):
        return obj.get_email()
    admin_email.short_description = ''

    def export_subscribers_csv(self, request, queryset):
        fields = (
            "id",
            ("email", lambda o: o.get_email()),
            ("name", lambda o: o.get_name()),
            "newsletter_id",
            "user_id",
            "subscribed",
            "unsubscribed",
        )
        return export_csv_response(export_csv(queryset, fields))
    export_subscribers_csv.short_description = _("Export to CSV")


admin.site.register(Subscriber, SubscriberAdmin)
admin.site.register(Newsletter, NewsletterAdmin)
