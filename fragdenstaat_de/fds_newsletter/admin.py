from django.db import transaction
from django.contrib import admin, messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.conf.urls import url
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from newsletter.admin import (
    SubmissionAdmin as BaseSubmissionAdmin,
    SubscriptionAdmin as BaseSubscriptionAdmin,
    NewsletterAdmin as BaseNewsletterAdmin
)
from newsletter.models import (
    Submission as BaseSubmission,
    Subscription,
    Newsletter
)

from froide.helper.csv_utils import export_csv, export_csv_response

from .models import Submission, Mailing
from .tasks import submit_submission, send_mailing


class MailingAdmin(admin.ModelAdmin):
    raw_id_fields = ('subscriptions', 'email_template')
    list_display = ('email_template', 'created', 'ready', 'sending_date', 'sending', 'sent')

    def get_urls(self):
        urls = super().get_urls()

        my_urls = [
            url(
                r'^(.+)/send/$',
                self.send,
                name='fds_newsletter_mailing_send'
            )
        ]

        return my_urls + urls

    def send(self, request, object_id):
        if request.method != 'POST':
            raise PermissionDenied
        if not self.has_change_permission(request):
            raise PermissionDenied

        mailing = get_object_or_404(Mailing, id=object_id)

        change_url = reverse(
            'admin:fds_newsletter_mailing_change', args=[object_id]
        )

        now = timezone.now()
        if mailing.sent or mailing.submitted:
            messages.error(request, _("Mailing already sent."))
            return redirect(change_url)

        if mailing.sending_date and mailing.sending_date < now:
            messages.error(request, _("Mailing sending date in the past."))
            return redirect(change_url)

        if mailing.subscriptions.all().count() == 0:
            if mailing.newsletter:
                mailing.subscriptions.set(mailing.newsletter.get_subscriptions())
            else:
                messages.info(request, _("Mailing has no newsletter and no recipients."))
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


class SubmissionAdmin(BaseSubmissionAdmin):
    raw_id_fields = ('subscriptions',)

    def submit(self, request, object_id):
        """ Overwrite and submit as task """
        submission = self._getobj(request, object_id)

        if submission.sent or submission.prepared:
            messages.info(request, _("Submission already sent."))
            change_url = reverse(
                'admin:fds_newsletter_submission_change', args=[object_id]
            )
            return redirect(change_url)

        if submission.subscriptions.all().count() == 0:
            message = submission.message
            submission.subscriptions.set(message.newsletter.get_subscriptions())

        submission.prepared = True
        submission.save()

        transaction.on_commit(lambda: submit_submission.delay(submission.id))

        messages.info(request, _("Your submission is being sent."))

        changelist_url = reverse('admin:fds_newsletter_submission_changelist')
        return redirect(changelist_url)


class NewsletterAdmin(BaseNewsletterAdmin):
    def admin_submissions(self, obj):
        return self._admin_url(obj, Submission, _("Submissions"))
    admin_submissions.short_description = ''


class SubscriptionAdmin(BaseSubscriptionAdmin):
    raw_id_fields = ('user',)
    actions = BaseSubscriptionAdmin.actions + ['export_subscribers_csv']

    def get_queryset(self, request):
        qs = super(SubscriptionAdmin, self).get_queryset(request)
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


admin.site.unregister(BaseSubmission)
admin.site.register(Submission, SubmissionAdmin)

admin.site.register(Mailing, MailingAdmin)

admin.site.unregister(Subscription)
admin.site.register(Subscription, SubscriptionAdmin)

admin.site.unregister(Newsletter)
admin.site.register(Newsletter, NewsletterAdmin)
