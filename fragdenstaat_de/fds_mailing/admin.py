import csv
import io

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, re_path, reverse
from django.utils import formats, timezone
from django.utils.html import format_html
from django.utils.translation import gettext as _

from cms.toolbar.utils import get_object_edit_url

from froide.account.admin import UserAdmin
from froide.follow.admin import FollowerAdmin
from froide.helper.admin_utils import (
    ForeignKeyFilter,
    make_choose_object_action,
    make_nullfilter,
)

from fragdenstaat_de.fds_newsletter.admin_utils import make_subscriber_tagger
from fragdenstaat_de.fds_newsletter.models import Subscriber
from fragdenstaat_de.theme.admin import PublicBodyAdmin

from .forms import RandomSplitForm
from .models import EmailTemplate, Mailing, MailingMessage
from .tasks import continue_sending
from .utils import add_fake_context


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "subject",
        "edit_link",
        "category",
        "mail_intent",
        "created",
        "updated",
        "active",
    )
    list_filter = (
        "active",
        "category",
    )
    search_fields = ("name", "subject", "mail_intent")
    date_hierarchy = "updated"

    @admin.display(description=_("Edit"))
    def edit_link(self, obj):
        edit_url = get_object_edit_url(obj)
        return format_html(
            '<a href="{}">{}</span>',
            edit_url,
            _("Edit"),
        )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:pk>/edit-body/",
                self.admin_site.admin_view(self.edit_body),
                name="fds_mailing-emailtemplate-edit_body",
            ),
            path(
                "<int:pk>/preview/",
                self.admin_site.admin_view(self.preview_html),
                name="fds_mailing-emailtemplate-preview",
            ),
            path(
                "<int:pk>/preview-eml/",
                self.admin_site.admin_view(self.preview_eml),
                name="fds_mailing-emailtemplate-preview_eml",
            ),
        ]
        return my_urls + urls

    def edit_body(self, request, pk):
        email_template = get_object_or_404(EmailTemplate, pk=pk)
        edit_url = get_object_edit_url(email_template)
        return redirect(edit_url)

    def preview_html(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied

        email_template = get_object_or_404(EmailTemplate, pk=pk)
        context = {"request": request}
        mail_intent = email_template.get_mail_intent()
        context = add_fake_context(context, mail_intent)
        html = email_template.get_body_html(context, preview=True)
        return HttpResponse(content=html.encode("utf-8"))

    def preview_eml(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied

        email_template = get_object_or_404(EmailTemplate, pk=pk)
        context = {"request": request}
        mail_intent = email_template.get_mail_intent()
        context = add_fake_context(context, mail_intent)

        content = email_template.get_email_bytes(context)
        return HttpResponse(content=content, content_type="message/rfc822")


class MailingAdmin(admin.ModelAdmin):
    raw_id_fields = ("email_template",)
    filter_horizontal = ("segments",)
    list_display = (
        "name",
        "email_template",
        "created",
        "newsletter",
        "segment_list",
        "ready",
        "recipients",
        "sending_date",
        "status",
        "open_rate",
        "publish",
    )
    list_filter = (
        "ready",
        "submitted",
        make_nullfilter("newsletter", "Newsletter"),
        "publish",
        "sending",
        "sent",
    )
    readonly_fields = (
        "created",
        "creator_user",
        "submitted",
        "sender_user",
        "sent_date",
        "sent",
        "open_count",
        "open_log_timestamp",
        "sending",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "newsletter",
                    "segments",
                )
            },
        ),
        (
            _("Mailing"),
            {
                "fields": (
                    "email_template",
                    "sender_name",
                    "sender_email",
                    "tracking",
                    "publish",
                    "sending_date",
                    "ready",
                )
            },
        ),
        (
            _("Status"),
            {
                "fields": (
                    "created",
                    "submitted",
                    "sending",
                    "sent",
                    "sent_date",
                    "open_count",
                    "open_log_timestamp",
                )
            },
        ),
        (
            _("User"),
            {
                "fields": (
                    "creator_user",
                    "sender_user",
                )
            },
        ),
    )
    search_fields = ("name",)
    actions = ["trigger_continue_sending", "tag_subscribers"]

    tag_subscribers = make_subscriber_tagger(
        None,
        convert_queryset_function=lambda qs: Subscriber.objects.filter(
            mailingmessage__mailing__in=qs
        ).distinct(),
    )

    def get_urls(self):
        urls = super().get_urls()

        my_urls = [
            re_path(r"^(.+)/send/$", self.send, name="fds_mailing_mailing_send"),
            path(
                "random-split/",
                self.admin_site.admin_view(self.random_split),
                name="fds_mailing-mailing-random_split",
            ),
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv),
                name="fds_mailing-mailing-import_csv",
            ),
        ]

        return my_urls + urls

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        qs = qs.annotate(
            total_recipients=models.Count("recipients"),
            sent_recipients=models.Count(
                "recipients", filter=models.Q(recipients__sent__isnull=False)
            ),
        )

        return qs.prefetch_related("email_template", "newsletter", "segments")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creator_user = request.user
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context["random_split_form"] = RandomSplitForm()
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description=_("Segments"))
    def segment_list(self, obj):
        return ", ".join([segment.name for segment in obj.segments.all()]) or "-"

    @admin.display(description=_("Status"))
    def status(self, obj):
        if not (obj.sending or obj.sent):
            if obj.submitted:
                return _("Submitted")
            if obj.ready:
                return _("Ready")
            else:
                return _("Draft")
        if obj.total_recipients == 0:
            return _("Not sent")
        sent_percentage = "{}%".format(
            formats.number_format(
                obj.sent_recipients / obj.total_recipients * 100, decimal_pos=1
            )
        )
        if obj.sending:
            return _("Sending...\u202f{}").format(sent_percentage)
        return _("Sent\u202f{}").format(sent_percentage)

    @admin.display(description=_("Recipients"))
    def recipients(self, obj):
        if obj.total_recipients == 0:
            return obj.get_recipient_count()
        return obj.total_recipients

    @admin.display(description=_("Open rate"))
    def open_rate(self, obj):
        if not obj.tracking:
            return "n/a"
        if not (obj.sending or obj.sent):
            return "..."
        if obj.total_recipients == 0:
            return "-"
        return "{}%".format(
            formats.number_format(
                obj.open_count / obj.total_recipients * 100, decimal_pos=3
            )
        )

    def trigger_continue_sending(self, request, queryset):
        for mailing in queryset:
            continue_sending.delay(mailing.id)

        self.message_user(
            request, _("Continue sending selected mailings."), level=messages.INFO
        )

    trigger_continue_sending.short_description = _("Continue sending mailing")

    def random_split(self, request):
        if not request.method == "POST":
            raise PermissionDenied
        if not self.has_add_permission(request):
            raise PermissionDenied

        form = RandomSplitForm(request.POST)
        if form.is_valid():
            form.save(user=request.user)
            self.message_user(
                request, _("Random split mailings created."), level=messages.INFO
            )
        else:
            self.message_user(
                request, _("Invalid form: {}").format(form.errors), level=messages.ERROR
            )
        return redirect("admin:fds_mailing_mailing_changelist")

    def import_csv(self, request):
        if not request.method == "POST":
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        csv_file = request.FILES.get("file")
        name = csv_file.name
        csv_file = io.StringIO(csv_file.read().decode("utf-8"))

        mailing = Mailing.objects.create(
            name=name, creator_user=request.user, publish=False
        )
        try:
            reader = csv.DictReader(csv_file)
            MailingMessage.objects.bulk_create(
                [
                    MailingMessage(
                        mailing=mailing,
                        name=row.get("name", ""),
                        email=row["email"],
                        user=None,
                    )
                    for row in reader
                ]
            )
        except Exception as e:
            self.message_user(request, str(e))
        else:
            self.message_user(request, _("CSV imported as mailing."))
        return redirect("admin:fds_mailing_mailing_changelist")

    def send(self, request, object_id):
        if request.method != "POST":
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        mailing = get_object_or_404(Mailing, id=object_id)

        change_url = reverse("admin:fds_mailing_mailing_change", args=[object_id])

        now = timezone.now()
        if mailing.sent or mailing.submitted:
            messages.error(request, _("Mailing already sent."))
            return redirect(change_url)

        if mailing.sending_date and mailing.sending_date < now:
            messages.error(request, _("Mailing sending date in the past."))
            return redirect(change_url)

        mailing.submit(request.user)

        messages.info(request, _("Your mailing is being sent."))

        return redirect(change_url)


class MailingMessageAdmin(admin.ModelAdmin):
    raw_id_fields = ("mailing", "subscriber", "donor", "user")
    list_display = ("mailing", "email", "name", "donor", "user", "sent", "bounced")
    date_hierarchy = "sent"
    list_filter = (
        "sent",
        "bounced",
        ("mailing", ForeignKeyFilter),
        ("donor", ForeignKeyFilter),
        ("subscriber", ForeignKeyFilter),
        ("user", ForeignKeyFilter),
    )
    search_fields = ("email", "name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related("donor", "subscriber", "user")
        return qs

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:pk>/preview/",
                self.admin_site.admin_view(self.preview_html),
                name="fds_mailing-mailingmessage-preview",
            ),
        ]
        return my_urls + urls

    def preview_html(self, request, pk):
        message = get_object_or_404(MailingMessage, id=pk)
        mailing = message.mailing
        email_template = mailing.email_template
        context = message.get_email_context()
        html = email_template.get_body_html(context, preview=True)
        return HttpResponse(content=html.encode("utf-8"))


# Monkey-Patch UserAdmin.send_mail to create mailing instead

original_send_mail = UserAdmin.send_mail


def send_mail(self, request, queryset):
    """
    Send mail to users

    """

    if request.POST.get("subject"):
        subject = request.POST.get("subject", "")
        mailing = Mailing.objects.create(
            creator_user=request.user, name=subject, publish=False
        )
        MailingMessage.objects.bulk_create(
            [
                MailingMessage(
                    mailing=mailing,
                    name=user.get_full_name(),
                    email=user.email,
                    user=user,
                )
                for user in queryset
            ]
        )
        change_url = reverse("admin:fds_mailing_mailing_change", args=[mailing.id])
        return redirect(change_url)

    return original_send_mail(self, request, queryset)


send_mail.short_description = _("Setup mailing to users...")
send_mail.allowed_permissions = ("change",)
UserAdmin.send_mail = send_mail


def execute_send_mail_template(admin, request, queryset, action_obj):
    count = queryset.count()
    if count != 1:
        admin.message_user(
            request, _("You can only send to one user at a time."), level=messages.ERROR
        )
        return
    for user in queryset:
        action_obj.send_to_user(user)

    admin.message_user(request, _("Email was sent."), level=messages.INFO)


UserAdmin.send_mail_template = make_choose_object_action(
    EmailTemplate, execute_send_mail_template, _("Send email via template...")
)
UserAdmin.actions += ["send_mail_template"]

# Monkey-Patch PublicBodyAdmin to create mailing for PublicBodies


def setup_mailing_publicbodies(admin, request, queryset, action_obj):
    mailing = Mailing.objects.create(
        name=_("Public Body Mailing"),
        creator_user=request.user,
        publish=False,
        email_template=action_obj,
    )
    MailingMessage.objects.bulk_create(
        [
            MailingMessage(mailing=mailing, name=pb.name, email=pb.email)
            for pb in queryset
        ]
    )
    admin.message_user(request, _("Mailing was set up."), level=messages.INFO)


PublicBodyAdmin.setup_mailing = make_choose_object_action(
    EmailTemplate, setup_mailing_publicbodies, _("Setup mailing for public bodies...")
)
PublicBodyAdmin.actions += ["setup_mailing"]


# Monkey-Patch Follow to create mailing for any follows


def setup_mailing_follow(admin, request, queryset, action_obj):
    mailing = Mailing.objects.create(
        name=_("Follow Mailing"),
        creator_user=request.user,
        publish=False,
        email_template=action_obj,
    )
    MailingMessage.objects.bulk_create(
        [
            MailingMessage(
                mailing=mailing, name=follow.get_full_name(), email=follow.get_email()
            )
            for follow in queryset
        ]
    )
    admin.message_user(request, _("Mailing was set up."), level=messages.INFO)


FollowerAdmin.setup_mailing = make_choose_object_action(
    EmailTemplate, setup_mailing_follow, _("Setup mailing for followers...")
)
FollowerAdmin.actions += ["setup_mailing"]

admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(Mailing, MailingAdmin)
admin.site.register(MailingMessage, MailingMessageAdmin)
