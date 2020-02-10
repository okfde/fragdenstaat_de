from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from froide_payment.models import PaymentStatus

from .services import send_donation_email, create_donation_from_payment
from .models import Donation
from .tasks import send_donation_notification


def payment_status_changed(sender=None, instance=None, **kwargs):
    order = instance.order
    domain_obj = order.get_domain_object()
    if not isinstance(domain_obj, Donation):
        obj = create_donation_from_payment(instance)
    else:
        obj = domain_obj
        domain_obj = None

    if not obj.payment_id:
        obj.payment = instance

    obj.amount_received = instance.received_amount or Decimal('0.0')

    if instance.status == PaymentStatus.CONFIRMED:
        obj.completed = True
        obj.received = True
        if instance.received_amount:
            obj.amount_reveived = instance.received_amount
        if not obj.received_timestamp:
            obj.received_timestamp = instance.received_timestamp
    elif instance.status in (
            PaymentStatus.ERROR, PaymentStatus.REFUNDED,
            PaymentStatus.REJECTED):
        obj.completed = False
        obj.received = False
    elif instance.status in (PaymentStatus.PENDING,):
        obj.completed = True
        obj.received = False
    elif instance.status in (PaymentStatus.INPUT, PaymentStatus.WAITING):
        obj.completed = False
        obj.received = False

    if obj.donor and obj.received and not obj.donor.active:
        obj.donor.active = True
        obj.donor.save()
    obj.save()

    now = timezone.now()
    if obj.received_timestamp:
        received_now = now - obj.received_timestamp <= timedelta(days=2)
    else:
        received_now = False

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

    pending_ok = False
    if payment.variant in ('lastschrift', 'banktransfer', 'sepa'):
        pending_ok = True
    confirmed = payment.status == PaymentStatus.CONFIRMED
    pending = payment.status == PaymentStatus.PENDING
    if (confirmed and received_now and not pending_ok) or (pending and pending_ok):
        send_donation_email(donation, domain_obj=domain_obj)
        transaction.on_commit(
            lambda: send_donation_notification.delay(donation.id)
        )
