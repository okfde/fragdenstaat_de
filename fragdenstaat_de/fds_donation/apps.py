from django.apps import AppConfig
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from fragdenstaat_de.fds_newsletter import unsubscribed


class FdsDonationConfig(AppConfig):
    name = "fragdenstaat_de.fds_donation"
    verbose_name = _("FragDenStaat Donations")

    def ready(self):
        from froide_payment.signals import sepa_notification, subscription_canceled
        from payments.signals import status_changed

        from froide.account import (
            account_canceled,
            account_email_changed,
            account_merged,
        )
        from froide.account.export import registry

        from fragdenstaat_de.fds_mailing import gather_mailing_preview_context
        from fragdenstaat_de.fds_newsletter import tag_subscriber

        from .listeners import (
            cancel_user,
            export_user_data,
            merge_user,
            payment_status_changed,
            remove_newsletter_subscriber,
            sepa_payment_processing,
            subscription_was_canceled,
            tag_subscriber_donor,
            user_email_changed,
        )

        status_changed.connect(payment_status_changed)
        subscription_canceled.connect(subscription_was_canceled)
        sepa_notification.connect(sepa_payment_processing)
        account_canceled.connect(cancel_user)
        account_email_changed.connect(user_email_changed)
        account_merged.connect(merge_user)
        unsubscribed.connect(remove_newsletter_subscriber)
        registry.register(export_user_data)
        tag_subscriber.connect(tag_subscriber_donor)
        gather_mailing_preview_context.connect(mailing_preview_context_listener)

        from froide.account.menu import MenuItem, menu_registry

        def get_donation_menu_item(request):
            return MenuItem(
                section="before_settings",
                order=999,
                url=reverse_lazy("fds_donation:donor-user"),
                label=_("My donations"),
            )

        menu_registry.register(get_donation_menu_item)


def mailing_preview_context_listener(sender, **kwargs):
    from fragdenstaat_de.fds_mailing import MailingPreviewContextProvider

    """Add the donation context to the mailing preview context."""
    return MailingPreviewContextProvider(
        name="donor",
        options={
            "no_donor": _("No donor"),
            "donor": _("One-time donor"),
            "user_donor": _("User donor"),
            "recent_donor": _("Recent donor"),
            "recurring_donor": _("Recurring donor"),
        },
        provide_context=get_donation_context,
    )


def get_donation_context(value, request):
    """Get the donation context for the mailing preview."""
    from fragdenstaat_de.fds_donation.models import Donor

    donor = Donor(
        first_name=request.user.first_name,
        last_name=request.user.first_name,
        address="Example Street 1",
        city="Example City",
        postcode="12345",
        email=request.user.email,
    )
    if value == "no_donor":
        return None
    elif value == "user_donor":
        donor.user = request.user
    elif value == "donor":
        donor.last_donation = None
    elif value == "recent_donor":
        donor.last_donation = timezone.now()
    elif value == "recurring_donor":
        donor.recurring_amount = 10
        donor.last_donation = timezone.now()
    return {
        "donor": donor,
    }
