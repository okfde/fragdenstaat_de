import json
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Max, Q, Sum
from django.utils import timezone

from froide_payment.models import PaymentStatus

from fragdenstaat_de.fds_newsletter.models import Subscriber

from .forms import SubscriptionCancelFeedbackForm
from .models import Donation, Donor, Recurrence
from .services import (
    create_donation_from_payment,
    detect_recurring_on_donor,
    send_donation_email,
    send_sepa_notification,
)
from .tasks import send_donation_notification


def payment_status_changed(sender=None, instance=None, **kwargs):
    order = instance.order
    domain_obj = order.get_domain_object()
    if not isinstance(domain_obj, Donation):
        obj = create_donation_from_payment(instance)
    else:
        obj = domain_obj
        domain_obj = None

    if not obj.payment_id or obj.payment_id != instance.id:
        obj.payment = instance

    obj.amount_received = instance.received_amount or Decimal("0.0")

    if instance.status == PaymentStatus.CONFIRMED:
        obj.completed = True
        # Set donation amount to what was actually captured by payment provider
        obj.amount = instance.captured_amount
        if instance.received_amount:
            obj.amount_reveived = instance.received_amount
        if instance.received_timestamp:
            obj.received_timestamp = instance.received_timestamp
        else:
            obj.received_timestamp = timezone.now()
    elif instance.status in (
        PaymentStatus.ERROR,
        PaymentStatus.REFUNDED,
        PaymentStatus.REJECTED,
        PaymentStatus.CANCELED,
    ):
        obj.received_timestamp = None
    elif instance.status in (PaymentStatus.PENDING, PaymentStatus.DEFERRED):
        obj.completed = True
        obj.received_timestamp = None
    elif instance.status in (PaymentStatus.INPUT, PaymentStatus.WAITING):
        obj.completed = False
        obj.received_timestamp = None

    if obj.donor and obj.received_timestamp and not obj.donor.active:
        obj.donor.active = True
        obj.donor.save()
    obj.save()

    now = timezone.now()
    if obj.received_timestamp:
        received_now = now - obj.received_timestamp <= timedelta(days=2)
    else:
        received_now = False

    detect_recurring_on_donor(obj.donor)
    process_new_donation(obj, received_now=received_now, domain_obj=domain_obj)


def process_new_donation(donation, received_now=False, domain_obj=None):
    payment = donation.payment
    if payment is None:
        return
    if not donation.completed:
        return
    if donation.recurring and not donation.first_recurring:
        # do not send email for recurring donations
        return

    pending_ok = payment.variant in ("lastschrift", "banktransfer", "sepa")
    confirmed = payment.status == PaymentStatus.CONFIRMED
    pending = payment.status in (PaymentStatus.PENDING, PaymentStatus.DEFERRED)
    if (confirmed and received_now and not pending_ok) or (pending and pending_ok):
        if not donation.email_sent:
            transaction.on_commit(lambda: send_donation_notification.delay(donation.id))
            send_donation_email(donation, domain_obj=domain_obj)


def subscription_was_canceled(sender, **kwargs):
    if sender is None:
        return

    Recurrence.objects.filter(subscription=sender).update(cancel_date=sender.canceled)


def user_email_changed(sender, old_email=None, **kwargs):
    try:
        # Connect user to existing
        confirmed_email_donor = Donor.objects.get(
            email=sender.email, user__isnull=True, email_confirmed__isnull=False
        )
        confirmed_email_donor.user = sender
        confirmed_email_donor.save()
    except Donor.DoesNotExist:
        pass


def cancel_user(sender, user=None, **kwargs):
    if user is None:
        return

    # remove user reference from donor as account is canceled
    Donor.objects.filter(user=user).update(user=None)


def merge_user(sender, old_user=None, new_user=None, **kwargs):
    Donor.objects.filter(user=old_user).update(user=new_user)


def sepa_payment_processing(sender, data=None, **kwargs):
    send_sepa_notification(sender, data)
    return True


def export_user_data(user):
    try:
        donor = Donor.objects.get(user=user)
    except Donor.DoesNotExist:
        return

    yield (
        "donor.json",
        json.dumps(
            {
                "salutation": donor.salutation,
                "first_name": donor.first_name,
                "last_name": donor.last_name,
                "company_name": donor.company_name,
                "address": donor.address,
                "postcode": donor.postcode,
                "city": donor.city,
                "country": str(donor.country),
                "email": donor.email,
                "attributes": dict(donor.attributes or {}) or None,
            }
        ).encode("utf-8"),
    )
    donations = Donation.objects.filter(donor=donor)
    yield (
        "donations.json",
        json.dumps(
            [
                {
                    "amount": float(d.amount),
                    "amount_received": (
                        float(d.amount_received) if d.amount_received else None
                    ),
                    "method": d.method,
                    "recurring": d.recurring,
                    "timestamp": d.timestamp.isoformat(),
                    "received_timestamp": (
                        d.received_timestamp.isoformat()
                        if d.received_timestamp
                        else None
                    ),
                }
                for d in donations
            ]
        ),
    )


def remove_newsletter_subscriber(sender: Subscriber, **kwargs):
    Donor.objects.filter(subscriber=sender).update(subscriber=None)


def tag_subscriber_donor(sender: Subscriber, email=None, **kwargs):
    add_tags = set()
    remove_tags = set()
    roughly_year = timedelta(days=370)
    high_value = 120
    a_year_ago = timezone.now() - roughly_year
    donor = (
        Donor.objects.filter(
            Q(subscriber=sender) | Q(email__iexact=email, email_confirmed__isnull=False)
        )
        .annotate(
            last_donation=Max(
                "donations__timestamp",
                filter=Q(donations__received_timestamp__isnull=False),
            ),
            amount_last_year=Sum(
                "donations__amount",
                filter=Q(donations__received_timestamp__gte=a_year_ago),
            ),
        )
        .first()
    )
    if not donor:
        return add_tags, remove_tags

    add_tags.add("donor")

    if donor.recurring_amount:
        add_tags.add("donor:recurring")
    else:
        remove_tags.add("donor:recurring")

    if donor.amount_last_year is not None and donor.amount_last_year >= high_value:
        add_tags.add("donor:highvalue")
    else:
        remove_tags.add("donor:highvalue")

    if donor.last_donation:
        if donor.last_donation > a_year_ago:
            add_tags.add("donor:active")
        else:
            add_tags.add("donor:inactive")
            remove_tags.add("donor:active")
    else:
        remove_tags.add("donor:active")

    return add_tags, remove_tags


def save_subscription_cancel_feedback(sender, data=None, **kwargs):
    if data is None:
        return
    form = SubscriptionCancelFeedbackForm(data=data)
    if form.is_valid():
        form.save(subscription=sender)
