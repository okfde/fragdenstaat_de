import logging
from datetime import timedelta
from decimal import Decimal
from typing import Optional, Tuple

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from dateutil.relativedelta import relativedelta

from froide.account.auth import try_login_user_without_mfa
from froide.account.models import User
from froide.account.services import AccountService
from froide.helper.auth import is_crew
from froide.helper.email_sending import mail_registry

from fragdenstaat_de.fds_newsletter.utils import subscribe_to_default_newsletter

from .models import Donation, Donor
from .tasks import process_recurrence_task
from .utils import merge_donors, propose_donor_merge, subscribe_donor_newsletter

logger = logging.getLogger(__name__)


new_donor_thanks_email = mail_registry.register(
    "fds_donation/email/donor_new_thanks",
    (
        "name",
        "first_name",
        "last_name",
        "salutation",
        "payment",
        "order",
        "donor",
        "donation",
    ),
)

donor_thanks_email = mail_registry.register(
    "fds_donation/email/donor_thanks",
    (
        "name",
        "first_name",
        "last_name",
        "salutation",
        "payment",
        "order",
        "donor",
        "donation",
    ),
)

donor_thanks_optin_email = mail_registry.register(
    "fds_donation/email/donor_thanks_optin",
    (
        "name",
        "first_name",
        "last_name",
        "salutation",
        "payment",
        "order",
        "donor",
        "donation",
    ),
)

donor_optin_email = mail_registry.register(
    "fds_donation/email/donor_optin",
    (
        "name",
        "first_name",
        "last_name",
        "salutation",
        "donor",
    ),
)

donation_reminder_email = mail_registry.register(
    "fds_donation/email/donation_reminder",
    (
        "name",
        "first_name",
        "last_name",
        "salutation",
        "donor",
        "donation",
        "payment",
        "order",
    ),
)


incomplete_donation_reminder_email = mail_registry.register(
    "fds_donation/email/incomplete_donation_reminder",
    (
        "name",
        "first_name",
        "last_name",
        "salutation",
        "donor",
        "donation",
        "payment",
        "order",
        "donate_url",
        "payment_url",
    ),
)

sepa_notification_email = mail_registry.register(
    "fds_donation/email/sepa_notification",
    (
        "name",
        "first_name",
        "last_name",
        "salutation",
        "donor",
        "payment",
        "order",
        "mandate_reference",
        "last4",
    ),
)

donation_gift_order_shipped_email = mail_registry.register(
    "fds_donation/email/donation_gift_order_shipped",
    (
        "gift_order",
        "name",
        "first_name",
        "last_name",
    ),
)


def get_or_create_donor(data, user=None, subscription=None):
    if user is not None:
        try:
            donor = Donor.objects.get(user=user)
            if subscription:
                donor.recurring_amount = subscription.plan.amount_year / 12
                donor.subscriptions.add(subscription)
            donor.save()
            return donor
        except Donor.DoesNotExist:
            return create_donor(data, user=user, subscription=subscription)
    if subscription is not None:
        donor = Donor.objects.filter(subscriptions=subscription).first()
        if donor is not None:
            return donor
    return create_donor(data, user=user, subscription=subscription)


def create_donor(data, user=None, subscription=None):
    email_confirmed = None
    if user is not None and user.email:
        if user.email.lower() == data["email"].lower():
            email_confirmed = user.date_joined
    recurring_amount = Decimal(0)
    if subscription:
        recurring_amount = subscription.plan.amount_year / 12
    donor = Donor.objects.create(
        salutation=data.get("salutation", ""),
        first_name=data["first_name"],
        last_name=data["last_name"],
        company_name=data.get("company_name", ""),
        address=data.get("address", ""),
        postcode=data.get("postcode", ""),
        city=data.get("city", ""),
        country=data.get("country", ""),
        email=data["email"].lower(),
        user=user,
        email_confirmed=email_confirmed,
        recurring_amount=recurring_amount,
        contact_allowed=data.get("contact", None),
        become_user=data.get("account", None),
        receipt=data.get("receipt", None),
    )
    if subscription:
        donor.subscriptions.add(subscription)
    logger.info("Donor created %s", donor.id)
    if donor.email_confirmed and donor.contact_allowed:
        subscribe_to_default_newsletter(donor.email, user=user)
        subscribe_donor_newsletter(donor)

    return donor


def send_donation_email(donation, domain_obj=None):
    if donation.email_sent:
        return
    donor = donation.donor
    if not donor.email:
        return

    extra_context = {}
    if donor.email_confirmed:
        needs_optin = False
        # No opt-in needed
        if donor.email_confirmation_sent:
            # not a new donor
            mail_intent = donor_thanks_email
        else:
            mail_intent = new_donor_thanks_email
    else:
        needs_optin = True
        mail_intent = donor_thanks_optin_email
        extra_context = {"action_url": donor.get_url()}

    if domain_obj is not None and not needs_optin:
        # payment not a donation
        # and no optin needed
        return

    context = {
        "name": donor.get_full_name(),
        "first_name": donor.first_name,
        "last_name": donor.last_name,
        "salutation": donor.get_salutation(),
        "payment": donation.payment,
        "order": donation.payment.order if donation.payment else None,
        "donor": donor,
        "donation": donation,
        "user": donor.user,
    }
    context.update(extra_context)

    mail_intent.send(
        user=donor.user,
        email=donor.email,
        context=context,
        ignore_active=True,
        priority=True,
    )
    donation.email_sent = timezone.now()
    donation.save()
    donor.email_confirmation_sent = donation.email_sent
    donor.save()
    return True


def send_donor_optin_email(donor):
    if not donor.email:
        return

    context = {
        "name": donor.get_full_name(),
        "first_name": donor.first_name,
        "last_name": donor.last_name,
        "salutation": donor.get_salutation(),
        "donor": donor,
        "user": donor.user,
        "action_url": donor.get_url(),
    }

    donor_optin_email.send(
        user=donor.user,
        email=donor.email,
        context=context,
        ignore_active=True,
        priority=True,
    )
    donor.email_confirmation_sent = timezone.now()
    donor.save()
    return True


def create_donation_from_payment(payment):
    order = payment.order
    try:
        return Donation.objects.get(models.Q(payment=payment) | models.Q(order=order))
    except Donation.DoesNotExist:
        pass
    # No donation, so no donor, let's create one
    donor = get_or_create_donor(
        {
            "email": order.user_email,
            "first_name": order.first_name,
            "last_name": order.last_name,
            "address": order.street_address_1,
            "city": order.city,
            "postcode": order.postcode,
            "country": order.country,
        },
        user=order.user,
        subscription=order.subscription,
    )
    domain_obj = order.get_domain_object()
    extra_kwargs = {}
    if not isinstance(domain_obj, Donation):
        if callable(getattr(domain_obj, "get_reference_data", None)):
            ref_data = domain_obj.get_reference_data()
            extra_kwargs["reference"] = ref_data.get("reference", "")
            extra_kwargs["keyword"] = ref_data.get("keyword", "")
    donation = Donation.objects.create(
        donor=donor,
        timestamp=order.created,
        amount=order.total_gross,
        amount_received=payment.received_amount or Decimal("0.0"),
        order=order,
        payment=payment,
        method=payment.variant,
        recurring=order.is_recurring,
        **extra_kwargs,
    )
    logger.info("Donation created %s", donation.id)
    return donation


def assign_and_merge_donors(donor, user):
    # Check if there's a confirmed donor with that user
    try:
        other_donor = Donor.objects.get(user=user, email_confirmed__isnull=False)
    except Donor.DoesNotExist:
        donor.user = user
        donor.save()
        return donor

    # Merge the two donors with the same user
    return merge_donor_list([donor, other_donor])


def merge_donor_list(donors):
    merged_donor = propose_donor_merge(donors)
    merged_donor.id = donors[0].id
    # Set uuid of first donor on merged donor to keep it
    merged_donor.uuid = donors[0].uuid
    candidates = [merged_donor, *donors[1:]]
    return merge_donors(candidates, merged_donor.id)


def confirm_donor_email(donor, request=None):
    if request and is_crew(request.user) and request.user != donor.user:
        # Don't trigger things as staff for different user
        return
    is_auth = request and request.user.is_authenticated

    donor.email_confirmed = timezone.now()
    donor.save()
    logger.info("Donor confirmed %s", donor.id)

    # Try finding existing user via email
    new_user = False
    user = None
    if not donor.user:
        # Find an active user with email
        user = User.objects.filter(
            email_deterministic=donor.email, is_active=True
        ).first()
        new_user = bool(user)
        if user is not None:
            donor = assign_and_merge_donors(donor, user)
            if request and not is_auth:
                # Login so user can access donation page
                try_login_user_without_mfa(request, user)

        elif donor.become_user and not is_auth:
            # Create user
            new_user = True
            user, created = AccountService.create_user(
                user_email=donor.email,
                first_name=donor.first_name,
                last_name=donor.last_name,
                address=donor.get_full_address(),
                private=True,
            )
            AccountService(user)._confirm_account()
            donor.user = user
            donor.save()
            logger.info("Donor user created %s for donor %s", user.id, donor.id)
            # Login new user
            if request:
                try_login_user_without_mfa(request, user)
    else:
        user = donor.user

    if "newsletter" in request.GET:
        donor.contact_allowed = True
        donor.save()

    if donor.contact_allowed:
        # Subscribe to normal and donor newsletter
        # TODO: subscribe email address / if different from user?
        subscribe_to_default_newsletter(
            donor.email,
            user=user,
            name=donor.get_full_name(),
            email_confirmed=True,
            reference="donation",
        )
        subscribe_donor_newsletter(donor, email_confirmed=True)
    if new_user:
        connect_payments_to_user(donor)


def connect_payments_to_user(donor):
    from froide_payment.models import Customer, Order, Subscription

    if not donor.user:
        return
    logger.info("Connect payments to donor %s", donor.id)

    donations_with_orders = donor.donations.all().filter(order__isnull=False)
    order_ids = donations_with_orders.values_list("order_id", flat=True)
    Order.objects.filter(id__in=order_ids).update(user=donor.user)
    logger.info("Connected orders to donor user %s: %s", donor.user.id, order_ids)
    sub_orders = Order.objects.filter(id__in=order_ids, subscription__isnull=False)
    sub_ids = set(sub_orders.values_list("subscription_id", flat=True))
    customer_ids = set(sub_orders.values_list("customer_id", flat=True))
    Customer.objects.filter(id__in=customer_ids, user__isnull=True).update(
        user=donor.user
    )
    logger.info("Connected customers to donor user %s: %s", donor.user.id, customer_ids)
    customer_ids = Subscription.objects.filter(
        id__in=sub_ids, customer__isnull=False
    ).values_list("customer_id", flat=True)
    Customer.objects.filter(id__in=customer_ids, user__isnull=True).update(
        user=donor.user
    )
    logger.info(
        "Connected more customers to donor user %s: %s", donor.user.id, customer_ids
    )


recurring_buckets = [  # in days
    (20, 40, 1),  # monthly
    (80, 100, 3),  # quarterly
    (160, 205, 6),  # half-yearly
    (340, 390, 12),  # yearly
]


def get_bucket(days: int) -> Optional[Tuple[int, int]]:
    for bucket in recurring_buckets:
        if bucket[0] <= days <= bucket[1]:
            return bucket
    return None


def detect_recurring_on_donor(donor):
    transaction.on_commit(lambda: process_recurrence_task.delay(donor.id))


def send_donation_reminder_email(donation):
    if donation.received_timestamp:
        return
    if donation.method != "banktransfer":
        return
    REMINDER_TEXT = "REMINDER:"
    if REMINDER_TEXT in donation.note:
        return

    now = timezone.now()
    diff = now - donation.timestamp
    if diff < timedelta(days=14):
        return

    donor = donation.donor
    context = {
        "name": donor.get_full_name(),
        "first_name": donor.first_name,
        "last_name": donor.last_name,
        "salutation": donor.get_salutation(),
        "payment": donation.payment,
        "order": donation.payment.order if donation.payment else None,
        "donor": donor,
        "donation": donation,
        "user": donor.user,
    }

    donation_reminder_email.send(
        user=donor.user,
        email=donor.email,
        context=context,
        ignore_active=True,
        priority=True,
    )
    donation.note += "\n\n{} {}\n".format(REMINDER_TEXT, now.isoformat())
    donation.note = donation.note.strip()
    donation.save()
    return True


def send_sepa_notification(payment, data):
    donation = create_donation_from_payment(payment)
    donor = donation.donor
    context = {
        "name": donor.get_full_name(),
        "first_name": donor.first_name,
        "last_name": donor.last_name,
        "salutation": donor.get_salutation(),
        "payment": payment,
        "order": payment.order,
        "donor": donor,
        "donation": donation,
        "user": donor.user,
    }
    context.update(data)

    sepa_notification_email.send(
        user=donor.user,
        email=donor.email,
        context=context,
        ignore_active=True,
        priority=True,
    )
    return True


def send_donation_gift_order_shipped(gift_order):
    if not gift_order.email:
        return
    context = {
        "name": gift_order.get_full_name(),
        "first_name": gift_order.first_name,
        "last_name": gift_order.last_name,
        "gift_order": gift_order,
    }

    return donation_gift_order_shipped_email.send(
        email=gift_order.email,
        context=context,
        ignore_active=True,
        priority=True,
    )


REMIND_INCOMPLETE_AFTER_DAYS = 2
DONATION_SPAM_COUNT = 6


def day_start(dt):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_incomplete_donations_to_remind(base_date=None):
    if base_date is None:
        base_date = timezone.now()
    base_date = timezone.localtime(base_date)

    start_date = day_start(base_date) - relativedelta(days=REMIND_INCOMPLETE_AFTER_DAYS)
    end_date = start_date + relativedelta(days=1)

    lookback_buffer = start_date - relativedelta(days=3)

    donations = (
        Donation.objects.filter(
            completed=False,
            received_timestamp__isnull=True,
            timestamp__gte=start_date,
            timestamp__lt=end_date,
        )
        .exclude(donor__email="")
        .order_by("timestamp")
        .select_related("donor", "payment")
    )

    donor_already = set()

    for donation in donations:
        if donation.donor_id in donor_already:
            continue
        donor_already.add(donation.donor.email.lower())

        donor_q = models.Q(donor_id=donation.donor_id) | models.Q(
            donor__email__iexact=donation.donor.email
        )

        donor_donation_count = (
            Donation.objects.filter(timestamp__gte=lookback_buffer)
            .filter(donor_q)
            .count()
        )
        if donor_donation_count >= DONATION_SPAM_COUNT:
            continue

        # Have we received any donations from this donor since?
        donation_from_donor_exists = (
            Donation.objects.filter(
                completed=True,
                timestamp__gte=lookback_buffer,
            )
            .filter(donor_q)
            .exists()
        )
        if donation_from_donor_exists:
            continue
        yield donation


INCOMPLETE_DONATION_NOTE = "IncompleteDonationReminder:"


def send_incomplete_donation_reminder(donation):
    if INCOMPLETE_DONATION_NOTE in donation.note:
        return
    donor = donation.donor
    if not donor.email:
        return

    context = {
        "name": donor.get_full_name(),
        "first_name": donor.first_name,
        "last_name": donor.last_name,
        "salutation": donor.get_salutation(),
        "payment": donation.payment,
        "order": donation.payment.order if donation.payment else None,
        "donor": donor,
        "donation": donation,
        "donate_url": donor.get_donate_url(),
        "payment_url": settings.SITE_URL + donation.payment.get_absolute_payment_url(),
    }

    incomplete_donation_reminder_email.send(
        user=donor.user,
        email=donor.email,
        context=context,
        ignore_active=True,
        priority=True,
    )
    donation.email_sent = timezone.now()
    donation.note += "{}: {}\n\n".format(
        INCOMPLETE_DONATION_NOTE, donation.email_sent.isoformat()
    )
    donation.save(update_fields=["email_sent", "note"])
    donor.email_confirmation_sent = donation.email_sent
    donor.save()
    return True


def remind_incomplete_donations():
    for donation in get_incomplete_donations_to_remind():
        send_incomplete_donation_reminder(donation)
