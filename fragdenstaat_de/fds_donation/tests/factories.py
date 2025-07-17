from datetime import timedelta
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory
from froide_payment.models import Customer, Order, Payment, Plan, Subscription
from froide_payment.provider.banktransfer import generate_transfer_code

from ..models import Donation, DonationGift, DonationGiftOrder, Donor


class DonorFactory(DjangoModelFactory):
    class Meta:
        model = Donor

    first_name = "Jane"
    last_name = factory.Sequence(lambda n: "D%se" % ("o" * min(20, int(n))))


class DonationFactory(DjangoModelFactory):
    class Meta:
        model = Donation

    donor = factory.SubFactory(DonorFactory)
    amount = Decimal("5.00")
    method = "banktransfer"


class DonationGiftFactory(DjangoModelFactory):
    class Meta:
        model = DonationGift

    name = factory.Sequence(lambda n: "Test Gift %s" % n)
    description = factory.Sequence(lambda n: "Description %s" % n)
    inventory = None


class DonationGiftOrderFactory(DjangoModelFactory):
    class Meta:
        model = DonationGiftOrder

    donation = factory.SubFactory(DonationFactory)
    donation_gift = factory.SubFactory(DonationGiftFactory)


def make_banktransfer_donation(donor, amount, date):
    plan = Plan.objects.create(
        name="Monthly Donation",
        slug="monthly-donation",
        interval=1,
        amount=amount,
    )
    customer = Customer.objects.create(user_email=donor.email)
    transfer_code = generate_transfer_code()
    subscription = Subscription.objects.create(
        plan=plan,
        customer=customer,
        remote_reference=transfer_code,
        created=date - timedelta(minutes=1),
        active=False,
    )
    order = Order.objects.create(
        user_email=donor.email,
        total_net=amount,
        total_gross=amount,
        remote_reference=transfer_code,
        is_donation=True,
        description="Monthly donation",
        subscription=subscription,
    )
    payment = Payment.objects.create(
        order=order,
        transaction_id=transfer_code,
    )
    donation = DonationFactory.create(
        donor=donor,
        method="banktransfer",
        timestamp=date,
        order=order,
        payment=payment,
        completed=True,
        amount=amount,
    )
    return donation
