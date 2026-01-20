from decimal import Decimal

from django.apps import AppConfig
from django.db.models.signals import post_save
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from fragdenstaat_de.fds_newsletter import unsubscribed


class FdsDonationNoConfig(AppConfig):
    name = "fragdenstaat_de.fds_donation"
    verbose_name = "FragDenStaat Donations (no config)"


class FroidePaymentNoConfig(AppConfig):
    name = "froide_payment"
    verbose_name = _("Froide Payment App (no config)")


class FdsDonationConfig(AppConfig):
    name = "fragdenstaat_de.fds_donation"
    verbose_name = _("FragDenStaat Donations")
    default = True

    def ready(self):
        from froide_payment.signals import (
            sepa_notification,
            subscription_cancel_feedback,
            subscription_canceled,
        )
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
            save_subscription_cancel_feedback,
            sepa_payment_processing,
            subscription_was_canceled,
            tag_subscriber_donor,
            user_email_changed,
        )
        from .models import Recurrence
        from .triggers import recurrence_created_trigger_listener

        status_changed.connect(payment_status_changed)
        subscription_canceled.connect(subscription_was_canceled)
        subscription_cancel_feedback.connect(save_subscription_cancel_feedback)
        sepa_notification.connect(sepa_payment_processing)
        account_canceled.connect(cancel_user)
        account_email_changed.connect(user_email_changed)
        account_merged.connect(merge_user)
        unsubscribed.connect(remove_newsletter_subscriber)
        registry.register(export_user_data)
        tag_subscriber.connect(tag_subscriber_donor)
        gather_mailing_preview_context.connect(
            mailing_donation_preview_context_listener
        )
        gather_mailing_preview_context.connect(mailing_payment_preview_context_listener)
        post_save.connect(recurrence_created_trigger_listener, sender=Recurrence)

        from froide.account.menu import MenuItem, menu_registry

        def get_donation_menu_item(request):
            try:
                return MenuItem(
                    section="before_settings",
                    order=999,
                    url=reverse("fds_donation:donor"),
                    label=_("My donations"),
                )
            except NoReverseMatch:
                # If the URL is not found, return None to avoid errors
                return None

        menu_registry.register(get_donation_menu_item)


def mailing_donation_preview_context_listener(sender, **kwargs):
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


def mailing_payment_preview_context_listener(sender, **kwargs):
    from fragdenstaat_de.fds_mailing import MailingPreviewContextProvider

    """Add the donation context to the mailing preview context."""
    return MailingPreviewContextProvider(
        name="payment",
        options={
            "no_payment": "---",
            "payment": _("One-time payment/order"),
            "recurring_payment": _("Recurring payment/order/subscription"),
        },
        provide_context=get_payment_context,
    )


def get_donation_context(value, request):
    """Get the donation context for the mailing preview."""
    from fragdenstaat_de.fds_donation.models import Donation, Donor

    donor = Donor(
        first_name=request.user.first_name,
        last_name=request.user.last_name,
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

    donation = Donation(
        amount=Decimal("10.00"),
        method="sepa",
    )
    return {"donor": donor, "donation": donation}


def get_payment_context(value, request):
    """Get payment context for the mailing preview."""
    from froide_payment.models import Customer, Order, Payment, Plan, Subscription

    data = {
        "first_name": request.user.first_name,
        "last_name": request.user.last_name,
        "street_address_1": "Example Street 1",
        "street_address_2": "",
        "city": "Example City",
        "postcode": "12345",
        "country": "DE",
    }

    amount = Decimal("10.00")
    variant = "banktransfer"

    order = Order(
        user_email=request.user.email,
        total_net=amount,
        total_gross=amount,
        is_donation=True,
        description="",
        kind="",
        remote_reference="FDS 12345",
        **data,
    )
    payment = Payment(
        total=amount,
        variant=variant,
        currency="EUR",
        order=order,
    )
    if value == "payment":
        return {
            "order": order,
            "payment": payment,
        }

    customer = Customer(user_email=request.user.email, provider="creditcard", **data)
    plan = Plan(
        name="Some Plan",
        slug="some-plan",
        category="donation",
        amount=amount,
        interval=1,
        amount_year=amount * Decimal(12),
        provider="creditcard",
        remote_reference="",
    )
    subscription = Subscription(active=False, customer=customer, plan=plan)
    order.subscription = subscription

    return {
        "order": order,
        "payment": payment,
        "subscription": subscription,
    }
