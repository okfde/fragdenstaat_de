from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import ugettext as _

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

from .models import Submission
from .tasks import submit_submission


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

        submit_submission.delay(submission.id)

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

admin.site.unregister(Subscription)
admin.site.register(Subscription, SubscriptionAdmin)

admin.site.unregister(Newsletter)
admin.site.register(Newsletter, NewsletterAdmin)
