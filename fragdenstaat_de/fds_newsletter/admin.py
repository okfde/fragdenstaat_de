from django.contrib import admin
from django.utils.translation import ugettext as _

from newsletter.admin import (
    SubscriptionAdmin as BaseSubscriptionAdmin,
    NewsletterAdmin as BaseNewsletterAdmin
)
from newsletter.models import (
    Submission,
    Subscription,
    Newsletter
)

from froide.helper.csv_utils import export_csv, export_csv_response

from fragdenstaat_de.fds_mailing.utils import SetupMailingMixin


class NewsletterAdmin(SetupMailingMixin, BaseNewsletterAdmin):
    list_display = (
        'title', 'visible'
    )
    actions = BaseNewsletterAdmin.actions + SetupMailingMixin.actions

    def setup_mailing_messages(self, mailing, queryset):
        if queryset.count() > 1:
            return _(
                'Failed to setup mailing: more than one newsletter selected!'
            )
        newsletter = queryset[0]
        mailing.newsletter = newsletter
        mailing.save()
        recipient_count = Subscription.objects.filter(
            newsletter=newsletter, subscribed=True
        ).count()
        return _(
            'Prepared mailing of newsletter {name} '
            'with currently {count} recipients').format(
                name=newsletter.title,
                count=recipient_count
        )


class SubscriptionAdmin(BaseSubscriptionAdmin):
    raw_id_fields = ('user',)
    actions = BaseSubscriptionAdmin.actions + ['export_subscribers_csv']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('newsletter')
        qs = qs.prefetch_related('user')
        return qs

    def export_subscribers_csv(self, request, queryset):
        fields = (
            "id", "email_field", "name_field", "newsletter_id",
            "user_id", "subscribed", "subscribe_date",
        )
        return export_csv_response(export_csv(queryset, fields))
    export_subscribers_csv.short_description = _("Export to CSV")


admin.site.unregister(Submission)

admin.site.unregister(Subscription)
admin.site.register(Subscription, SubscriptionAdmin)

admin.site.unregister(Newsletter)
admin.site.register(Newsletter, NewsletterAdmin)
