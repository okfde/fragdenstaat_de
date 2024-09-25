from django.contrib import admin
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.db.models.functions import Cast, Collate, ExtractDay, Now, TruncDate
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from froide.helper.admin_utils import make_daterangefilter, make_rangefilter
from froide.helper.csv_utils import export_csv, export_csv_response

from fragdenstaat_de.fds_mailing.models import MailingMessage
from fragdenstaat_de.fds_mailing.utils import SetupMailingMixin

from .forms import SubscriberImportForm
from .models import Newsletter, Subscriber, UnsubscribeFeedback
from .utils import unsubscribe_queryset


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ("title", "visible", "subscriber_count", "admin_subscribers")
    prepopulated_fields = {"slug": ("title",)}

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:pk>/import-csv/",
                self.admin_site.admin_view(self.import_csv),
                name="fds_newsletter-import_csv",
            ),
        ]
        return my_urls + urls

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

    def import_csv(self, request, pk):
        newsletter = Newsletter.objects.get(pk=pk)
        if request.method == "POST":
            form = SubscriberImportForm(request.POST, request.FILES)
            if form.is_valid():
                form.save(newsletter)
                self.message_user(request, _("Subscribers imported."))
                return redirect("admin:fds_newsletter_newsletter_change", pk)
        else:
            form = SubscriberImportForm()
        opts = self.model._meta
        ctx = {
            "app_label": opts.app_label,
            "opts": opts,
            "form": form,
            "object": newsletter,
        }
        return render(request, "fds_newsletter/admin/import_csv.html", ctx)


@admin.register(Subscriber)
class SubscriberAdmin(SetupMailingMixin, admin.ModelAdmin):
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
        make_daterangefilter("subscribed", _("Subscribed date")),
        "unsubscribed",
        make_daterangefilter("unsubscribed", _("Unsubscribed date")),
        make_rangefilter("days_subscribed", _("Days subscribed")),
        "reference",
        "unsubscribe_method",
        "tags",
    )
    search_fields = ("email", "user_email_deterministic", "keyword")
    readonly_fields = ("created", "activation_code")
    date_hierarchy = "created"
    actions = ["unsubscribe", "export_subscribers_csv"] + SetupMailingMixin.actions

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("newsletter")
        qs = qs.select_related("user")
        qs = qs.annotate(
            user_email_deterministic=Collate("user__email", "und-x-icu"),
        )
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

    def setup_mailing_messages(self, mailing, queryset):
        queryset = queryset.exclude(subscribed__isnull=True)

        count = queryset.count()
        MailingMessage.objects.bulk_create(
            [
                MailingMessage(mailing_id=mailing.id, subscriber_id=subscriber_id)
                for subscriber_id in queryset.values_list("id", flat=True)
            ]
        )

        return _("Prepared mailing to subscribers with {count} recipients").format(
            count=count
        )


@admin.register(UnsubscribeFeedback)
class UnsubscribeFeedbackAdmin(admin.ModelAdmin):
    list_display = ("reason", "comment", "created")
    list_filter = ("reason", "created")
    search_fields = ("comment",)
    date_hierarchy = "created"
    raw_id_fields = ("subscriber",)
