from decimal import Decimal

from django.conf import settings
from django.utils import timezone

import pytest
from froide_payment.models import Order, Payment, PaymentStatus
from froide_payment.provider.banktransfer import generate_transfer_code

from ..external import find_donation, import_banktransfer, make_transfer_ident
from ..models import Donation
from ..recurrence import process_recurrence_on_donor
from .factories import DonationFactory, DonorFactory, make_banktransfer_donation


@pytest.mark.django_db
def test_import_banktransfer_new_iban():
    transfer_code = generate_transfer_code()
    donor = DonorFactory.create(attributes={"iban": "DE0"})
    donation = DonationFactory.create(
        donor=donor,
        payment=Payment.objects.create(
            transaction_id=transfer_code, order=Order.objects.create()
        ),
    )

    iban = "DE1"
    row = {
        "reference": transfer_code,
        "iban": iban,
    }
    found_donation = find_donation("no-ident", row)
    assert found_donation == donation
    donor = found_donation.donor
    donor.refresh_from_db()
    assert donor.attributes["iban"] == iban
    assert iban in donor.attributes["ibans"]


@pytest.mark.django_db
def test_import_banktransfer_subscription_active():
    donor = DonorFactory.create()
    now = timezone.now()
    first_date = now
    amount = Decimal("10.00")
    donation = make_banktransfer_donation(donor, amount, first_date)
    transfer_code = donation.payment.transaction_id

    iban = "DE1"
    row = {
        "reference": transfer_code,
        "iban": iban,
        "amount": amount,
        "date": first_date,
        "date_received": first_date,
    }
    import_banktransfer(transfer_code, row, settings.DONATION_PROJECTS[0][0])

    payment = donation.payment
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.CONFIRMED
    assert payment.captured_amount == amount
    assert payment.received_amount == amount
    assert payment.received_timestamp == first_date

    subscription = payment.order.subscription
    subscription.refresh_from_db()
    assert subscription.active is True


@pytest.mark.django_db
def test_import_banktransfer_purpose(donor):
    now = timezone.now()
    first_date = now
    amount = Decimal("10.00")
    donation = make_banktransfer_donation(donor, amount, first_date)
    transfer_code = donation.payment.transaction_id

    assert donation.purpose == ""

    iban = "DE1"
    row = {
        "reference": transfer_code,
        "iban": iban,
        "amount": amount,
        "date": first_date,
        "date_received": first_date,
        "purpose": "TEST-PURP",
    }
    import_banktransfer(transfer_code, row, settings.DONATION_PROJECTS[0][0])

    payment = donation.payment
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.CONFIRMED

    donation.refresh_from_db()
    assert donation.purpose == "TEST-PURP"

    subscription = payment.order.subscription
    subscription.refresh_from_db()
    assert subscription.active is True


@pytest.mark.django_db
def test_import_banktransfer_keep_purpose(donor):
    now = timezone.now() - timezone.timedelta(days=60)
    first_date = now
    amount = Decimal("10.00")
    donation = make_banktransfer_donation(donor, amount, first_date)
    transfer_code = donation.payment.transaction_id
    donation.purpose = "PURPOSE-1"
    donation.identifier = make_transfer_ident(
        {
            "reference": transfer_code,
            "iban": "DE1",
            "amount": amount,
            "date": first_date,
            "date_received": first_date,
        },
        index=0,
    )
    donation.received_timestamp = first_date
    donation.amount_received = amount
    donation.save()

    next_date = first_date + timezone.timedelta(days=30)

    iban = "DE1"
    row = {
        "reference": transfer_code,
        "iban": iban,
        "amount": amount,
        "date": next_date,
        "date_received": next_date,
    }
    transfer_ident = make_transfer_ident(row, index=0)

    import_banktransfer(
        transfer_ident,
        row,
        settings.DONATION_PROJECTS[0][0],
    )
    process_recurrence_on_donor(donor)
    donation = Donation.objects.get(timestamp__date=next_date, donor=donor)

    assert donation.purpose == "PURPOSE-1"
    assert donation.identifier == transfer_ident
