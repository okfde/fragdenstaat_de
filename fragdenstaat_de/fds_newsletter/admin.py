from django.contrib import admin
from django.db.models import (
    Q,
    F,
    Count,
    Value,
    IntegerField,
    Case,
    When,
)
from django.db.models.functions import Cast, ExtractDay, TruncDate, Now
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from froide.helper.admin_utils import DateRangeFilter, make_rangefilter
from froide.helper.csv_utils import export_csv, export_csv_response

from fragdenstaat_de.fds_mailing.utils import SetupMailingMixin

from .models import Newsletter, Subscriber
from .utils import unsubscribe_queryset


class NewsletterAdmin(SetupMailingMixin, admin.ModelAdmin):
    list_display = ("title", "visible", "subscriber_count", "admin_subscribers")
    prepopulated_fields = {"slug": ("title",)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            subscriber_count=Count(
                "subscribers", filter=Q(subscribers__subscribed__isnull=False)
            )
        )
        return qs

    def subscriber_count(self, obj):
        return obj.subscriber_count

    subscriber_count.admin_order_field = "subscriber_count"
    subscriber_count.short_description = _("active subscriber count")

    def admin_subscribers(self, obj):
        url = reverse(
            "admin:fds_newsletter_subscriber_changelist",
            current_app=self.admin_site.name,
        )

        return format_html(
            '<a href="{}?newsletter__id__exact={}">{}</a>',
            url,
            obj.id,
            _("See all subscribers"),
        )

    admin_subscribers.short_description = ""


class SubscriberAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = (
        "admin_email",
        "newsletter",
        "created",
        "days_subscribed",
        "subscribed",
        "unsubscribed",
        "reference",
        "keyword",
    )
    list_filter = (
        "newsletter",
        "subscribed",
        ("subscribed", DateRangeFilter),
        "unsubscribed",
        ("unsubscribed", DateRangeFilter),
        make_rangefilter("days_subscribed", _("Days subscribed")),
        "reference",
        "unsubscribe_method",
        "tags",
    )
    search_fields = ("email", "user__email", "keyword")
    readonly_fields = ("created", "activation_code")
    date_hierarchy = "created"
    actions = ["unsubscribe", "export_subscribers_csv"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("newsletter")
        qs = qs.prefetch_related("user")
        qs = qs.annotate(
            days_subscribed=Case(
                When(subscribed=None, unsubscribed=None, then=Value(0)),
                When(
                    subscribed=None,
                    then=Cast(
                        ExtractDay(
                            TruncDate(F("unsubscribed")) - TruncDate(F("created"))
                        ),
                        IntegerField(),
                    ),
                ),
                default=Cast(
                    ExtractDay(TruncDate(Now()) - TruncDate(F("subscribed"))),
                    IntegerField(),
                ),
                output_field=IntegerField(),
            )
        )
        return qs

    def admin_email(self, obj):
        return obj.get_email()

    admin_email.short_description = ""

    def days_subscribed(self, obj):
        return obj.days_subscribed

    days_subscribed.admin_order_field = "days_subscribed"
    days_subscribed.short_description = _("Days subscribed")

    def unsubscribe(self, request, queryset):
        queryset = queryset.filter(subscribed__isnull=False)
        unsubscribe_queryset(queryset, method="admin")

    unsubscribe.short_description = _("Unsubscribe")

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
