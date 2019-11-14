from froide_payment.models import PaymentStatus

from .services import send_donation_email, create_donation_from_payment
from .models import Donation


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

    if instance.status == PaymentStatus.CONFIRMED:
        obj.completed = True
        obj.received = True

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

    if obj.completed:
        send_donation_email(obj, domain_obj=domain_obj)
    if obj.donor and obj.received and not obj.donor.active:
        obj.donor.active = True
        obj.donor.save()
    obj.save()
