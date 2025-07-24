from django import forms
from django.conf import settings
from django.contrib import admin
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.db.models.functions import Cast, Collate, ExtractDay, Now, TruncDate
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse, reverse_lazy
from django.utils.html import format_html
from django.utils.translation import gettext as _

from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from froide.helper.admin_utils import (
    MultiFilterMixin,
    TaggitListFilter,
    make_batch_tag_action,
    make_daterangefilter,
    make_rangefilter,
)
from froide.helper.csv_utils import export_csv, export_csv_response
from froide.helper.widgets import TagAutocompleteWidget

from fragdenstaat_de.fds_mailing.models import MailingMessage
from fragdenstaat_de.fds_mailing.utils import SetupMailingMixin

from .forms import SubscriberImportForm
from .models import (
    SUBSCRIBER_TAG_AUTOCOMPLETE_URL,
    Newsletter,
    Segment,
    Subscriber,
    SubscriberTag,
    TaggedSegment,
    TaggedSubscriber,
    UnsubscribeFeedback,
)
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


class SubscriberTagListFilter(MultiFilterMixin, TaggitListFilter):
    tag_class = TaggedSubscriber
    title = "Tags"
    parameter_name = "tags__slug"
    lookup_name = "__in"


class SubscriberAdminForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = "__all__"
        widgets = {
            "tags": TagAutocompleteWidget(
                autocomplete_url=SUBSCRIBER_TAG_AUTOCOMPLETE_URL,
                allow_new=False,
            ),
        }


@admin.register(Subscriber)
class SubscriberAdmin(SetupMailingMixin, admin.ModelAdmin):
    form = SubscriberAdminForm
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
        "tag_list",
    )
    list_filter = (
        "newsletter",
        "subscribed",
        make_daterangefilter("subscribed", _("Subscribed date")),
        "unsubscribed",
        make_daterangefilter("unsubscribed", _("Unsubscribed date")),
        make_rangefilter("days_subscribed", _("Days subscribed")),
        SubscriberTagListFilter,
        "unsubscribe_method",
        "reference",
    )
    search_fields = ("email", "user_email_deterministic", "keyword")
    readonly_fields = ("created", "activation_code")
    date_hierarchy = "created"
    actions = [
        "unsubscribe",
        "export_subscribers_csv",
        "update_tags",
        "tag_all",
    ] + SetupMailingMixin.actions

    tag_all = make_batch_tag_action(
        field="tags", autocomplete_url=SUBSCRIBER_TAG_AUTOCOMPLETE_URL
    )

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
        qs = qs.prefetch_related("tags")
        return qs

    def tag_list(self, obj):
        return ", ".join([str(tag) for tag in obj.tags.all()])

    def admin_email(self, obj):
        return obj.get_email()

    admin_email.short_description = ""

    def days_subscribed(self, obj):
        return obj.days_subscribed

    days_subscribed.admin_order_field = "days_subscribed"
    days_subscribed.short_description = _("Days subscribed")

    @admin.action(description=_("Unsubscribe"))
    def unsubscribe(self, request, queryset):
        queryset = queryset.filter(subscribed__isnull=False)
        unsubscribe_queryset(queryset, method="admin")

    @admin.action(description=_("Update tags"))
    def update_tags(self, request, queryset):
        for subscriber in queryset:
            subscriber.update_tags()

    @admin.action(description=_("Export to CSV"))
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

    def setup_mailing_messages(self, mailing, queryset):
        queryset = queryset.exclude(subscribed__isnull=True)

        count = queryset.count()
        MailingMessage.objects.bulk_create(
            [
                MailingMessage(
                    mailing_id=mailing.id,
                    subscriber=subscriber,
                    email=subscriber.get_email(),
                    name=subscriber.get_name(),
                )
                for subscriber in queryset
            ]
        )

        return _("Prepared mailing to subscribers with {count} recipients").format(
            count=count
        )


@admin.register(SubscriberTag)
class SubscriberTagAdmin(admin.ModelAdmin):
    list_display = ("name", "subscriber_count")
    search_fields = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            subscriber_count=Count(
                "subscribers",
                filter=Q(subscribers__content_object__subscribed__isnull=False),
            )
        )
        return qs

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "auto-complete/",
                self.admin_site.admin_view(self.autocomplete),
                name="fds_newsletter-subscribertag-autocomplete",
            ),
        ]
        return my_urls + urls

    def autocomplete(self, request):
        qs = SubscriberTag.objects.all()
        if "q" in request.GET:
            qs = qs.filter(name__icontains=request.GET["q"])
        qs = qs.order_by("name").values_list("name", flat=True)
        return JsonResponse({"objects": [{"value": tag, "label": tag} for tag in qs]})

    def subscriber_count(self, obj):
        return obj.subscriber_count

    subscriber_count.admin_order_field = "subscriber_count"
    subscriber_count.short_description = _("active subscriber count")


SegmentAdminBaseForm = movenodeform_factory(Segment)


class SegmentAdminForm(SegmentAdminBaseForm):
    class Meta:
        model = Segment
        exclude = SegmentAdminBaseForm.Meta.exclude
        widgets = {
            "tags": TagAutocompleteWidget(
                autocomplete_url=reverse_lazy(
                    "admin:fds_newsletter-subscribertag-autocomplete"
                ),
                allow_new=False,
            ),
        }


class SubscriberTagSegmentListFilter(MultiFilterMixin, TaggitListFilter):
    tag_class = TaggedSegment
    title = "Tags"
    parameter_name = "tags__slug"
    lookup_name = "__in"


@admin.register(Segment)
class SegmentAdmin(TreeAdmin):
    form = SegmentAdminForm
    list_display = ("name", "created", "tag_list", "subscriber_count")
    search_fields = ("name",)
    date_hierarchy = "created"
    list_filter = [SubscriberTagSegmentListFilter]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related("tags")
        return qs

    def tag_list(self, obj):
        tags = ", ".join([str(tag) for tag in obj.tags.all()])
        if tags and obj.negate:
            tags = f"NOT ({tags})"
        return tags

    def get_default_newsletter(self):
        if not hasattr(self, "_newsletter"):
            try:
                self._newsletter = Newsletter.objects.get(
                    slug=settings.DEFAULT_NEWSLETTER
                )
            except Newsletter.DoesNotExist:
                self._newsletter = None
        return self._newsletter

    def subscriber_count(self, obj):
        # FIXME: n+1 query with ballooning joins
        return obj.get_subscribers(newsletter=self.get_default_newsletter()).count()

    subscriber_count.admin_order_field = "subscriber_count"
    subscriber_count.short_description = _("active subscriber count")


@admin.register(UnsubscribeFeedback)
class UnsubscribeFeedbackAdmin(admin.ModelAdmin):
    list_display = ("reason", "comment", "created")
    list_filter = ("reason", "created")
    search_fields = ("comment",)
    date_hierarchy = "created"
    raw_id_fields = ("subscriber",)
