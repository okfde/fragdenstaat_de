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


admin.site.unregister(BaseSubmission)
admin.site.register(Submission, SubmissionAdmin)

admin.site.unregister(Subscription)
admin.site.register(Subscription, SubscriptionAdmin)

admin.site.unregister(Newsletter)
admin.site.register(Newsletter, NewsletterAdmin)
