from datetime import timedelta

from django.conf import settings
from django.dispatch import receiver
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from fragdenstaat_de.fds_newsletter.models import Subscriber

from . import MailingPreviewContextProvider, gather_mailing_preview_context


@receiver(gather_mailing_preview_context)
def provide_user_context(sender, **kwargs):
    def get_info(value, request):
        if value == "no_user":
            return
        return {
            "user": request.user,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
        }

    return MailingPreviewContextProvider(
        "user",
        {
            "no_user": _("---"),
            "user": _("User"),
        },
        get_info,
    )


@receiver(gather_mailing_preview_context)
def provide_subscriber_context(sender, **kwargs):
    def get_subscriber_info(value, request):
        from fragdenstaat_de.fds_newsletter.models import Newsletter, get_email_context

        if value == "no_subscriber":
            return
        subscriber = Subscriber(
            pk=0,
            subscribed=timezone.now(),
            email=request.user.email,
            name=request.user.get_full_name(),
            newsletter=Newsletter.objects.get_default(),
        )
        if value == "old_subscriber":
            subscriber.subscribed -= timedelta(days=365)
        elif value == "subscriber_user":
            subscriber.user = request.user
        return get_email_context(subscriber)

    return MailingPreviewContextProvider(
        "newsletter_subscriber",
        {
            "no_subscriber": _("---"),
            "new_subscriber": _("New subscriber"),
            "old_subscriber": _("Old Subscriber"),
            "subscriber_user": _("User Subscriber"),
        },
        get_subscriber_info,
    )


@receiver(gather_mailing_preview_context)
def provide_action_context(sender, **kwargs):
    def get_action_info(value, request):
        if value == "no_action":
            return
        return {
            "action_label": _("Example Action label!"),
            "action_url": settings.SITE_URL + "/example-action/",
        }

    return MailingPreviewContextProvider(
        "action",
        {
            "no_action": _("---"),
            "has_action": _("Has action"),
        },
        get_action_info,
    )


@receiver(gather_mailing_preview_context)
def provide_searchalert_context(sender, **kwargs):
    def get_searchalert_info(value, request):
        from froide.searchalert.configuration import AlertEvent, AlertSection
        from froide.searchalert.models import Alert

        if value == "no_alert":
            return
        alert = Alert(
            pk=0,
            email_confirmed=timezone.now(),
            user=request.user,
            query=request.user.get_full_name(),
            sections={"foirequest": True},
        )

        return {
            "alert": alert,
            "total_count": 13,
            "sections": [
                AlertSection(
                    key="foirequest",
                    title="Example section",
                    url="http://example.com",
                    results=[
                        AlertEvent(
                            title="Example title",
                            url="http://example.org",
                            content=mark_safe("highlighted <em>text</em> parts"),
                        )
                    ],
                    result_count=1,
                )
            ],
            "since_date": timezone.now() - alert.get_relative_delta(),
        }

    return MailingPreviewContextProvider(
        "searchalert_alert",
        {
            "no_alert": _("---"),
            "alert": _("Provide alert"),
        },
        get_searchalert_info,
    )
