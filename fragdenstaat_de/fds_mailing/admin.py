from django.db import transaction, models
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.conf.urls import url
from django.urls import reverse
from django.utils import timezone

from cms.admin.placeholderadmin import PlaceholderAdminMixin
from cms.models.static_placeholder import StaticPlaceholder

from froide.helper.admin_utils import ForeignKeyFilter, make_nullfilter

from .models import EmailTemplate, Mailing, MailingMessage
from .tasks import send_mailing, continue_sending


class EmailTemplateAdmin(PlaceholderAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'category', 'created', 'updated',)
    list_filter = (
        'category',
    )
    search_fields = ('name', 'subject',)
    date_hierarchy = 'updated'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            url(r'^(?P<pk>\d+)/edit-body/$',
                self.admin_site.admin_view(self.edit_body),
                name='fds_mailing-emailtemplate-edit_body'),
            url(r'^(?P<pk>\d+)/preview/$',
                self.admin_site.admin_view(self.preview),
                name='fds_mailing-emailtemplate-preview'),
            url(r'^(?P<pk>\d+)/preview-eml/$',
                self.admin_site.admin_view(self.preview_eml),
                name='fds_mailing-emailtemplate-preview_eml'),
        ]
        return my_urls + urls

    def edit_body(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied

        email_template = get_object_or_404(EmailTemplate, pk=pk)
        static_placholder = email_template.get_extra_placeholder_name()
        static_placeholder_id = None
        if static_placholder:
            try:
                static_placeholder_id = StaticPlaceholder.objects.get(code=static_placholder).pk
            except StaticPlaceholder.DoesNotExist:
                pass

        return render(request, 'fds_mailing/emailtemplate_update_form.html', {
            'object': email_template,
            'static_placeholder_id': static_placeholder_id
        })

    def preview(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied

        email_template = get_object_or_404(EmailTemplate, pk=pk)
        content = email_template.render_email_html().encode('utf-8')
        return HttpResponse(content=content)

    def preview_eml(self, request, pk):
        if not self.has_change_permission(request):
            raise PermissionDenied

        email_template = get_object_or_404(EmailTemplate, pk=pk)
        content = email_template.get_email_bytes({'request': request})
        return HttpResponse(
            content=content, content_type='message/rfc822'
        )


class MailingAdmin(admin.ModelAdmin):
    raw_id_fields = ('email_template', 'newsletter')
    list_display = (
        'name', 'email_template', 'created', 'newsletter',
        'ready', 'sending_date', 'sending', 'sent',
        'sent_percentage', 'publish'
    )
    list_filter = (
        'ready', 'submitted',
        make_nullfilter('newsletter', 'Newsletter'),
        'publish', 'sending', 'sent',
    )
    search_fields = ('name',)
    actions = ['trigger_continue_sending']

    def get_urls(self):
        urls = super().get_urls()

        my_urls = [
            url(
                r'^(.+)/send/$',
                self.send,
                name='fds_mailing_mailing_send'
            )
        ]

        return my_urls + urls

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        qs = qs.annotate(
            total_recipients=models.Count('recipients'),
            sent_recipients=models.Count(
                'recipients', filter=models.Q(recipients__sent__isnull=False)
            ),
        )

        return qs.select_related('email_template', 'newsletter')

    def sent_percentage(self, obj):
        if obj.total_recipients == 0:
            return '-'
        return '{0:.2f}%'.format(
            obj.sent_recipients / obj.total_recipients * 100
        )

    def trigger_continue_sending(self, request, queryset):
        for mailing in queryset:
            continue_sending.delay(mailing.id)

        self.message_user(
            request, _('Continue sending selected mailings.'),
            level=messages.INFO
        )
    trigger_continue_sending.short_description = _("Continue sending mailing")

    def send(self, request, object_id):
        if request.method != 'POST':
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        mailing = get_object_or_404(Mailing, id=object_id)

        change_url = reverse(
            'admin:fds_mailing_mailing_change', args=[object_id]
        )

        now = timezone.now()
        if mailing.sent or mailing.submitted:
            messages.error(request, _("Mailing already sent."))
            return redirect(change_url)

        if mailing.sending_date and mailing.sending_date < now:
            messages.error(request, _("Mailing sending date in the past."))
            return redirect(change_url)

        mailing.submitted = True
        if not mailing.sending_date:
            mailing.sending_date = timezone.now()
        mailing.save()

        transaction.on_commit(lambda: send_mailing.apply_async(
            (mailing.id, mailing.sending_date),
            eta=mailing.sending_date,
            retry=False
        ))

        messages.info(request, _("Your mailing is being sent."))

        return redirect(change_url)


class MailingMessageAdmin(admin.ModelAdmin):
    raw_id_fields = ('mailing', 'subscription', 'donor', 'user')
    list_display = ('mailing', 'email', 'name', 'donor', 'user', 'sent', 'bounced')
    list_filter = (
        'sent', 'bounced',
        ('mailing', ForeignKeyFilter),
        ('donor', ForeignKeyFilter),
        ('subscription', ForeignKeyFilter),
        ('user', ForeignKeyFilter),
    )
    search_fields = ('email', 'name')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related('donor', 'subscription', 'user')
        return qs


admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(Mailing, MailingAdmin)
admin.site.register(MailingMessage, MailingMessageAdmin)
