from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

import pytest
from froide_payment.models import Order, Payment

from ..services import (
    DONATION_SPAM_COUNT,
    INCOMPLETE_DONATION_NOTE,
    REMIND_INCOMPLETE_AFTER_DAYS,
    get_incomplete_donations_to_remind,
    send_incomplete_donation_reminder,
)
from .factories import DonationFactory, DonorFactory


@pytest.mark.django_db
def test_incomplete_donations_remind_not_yet():
    timestamp = timezone.now()
    donor = DonorFactory(email="test@example.com")
    DonationFactory(donor=donor, completed=False, timestamp=timestamp)
    assert len(list(get_incomplete_donations_to_remind())) == 0


@pytest.mark.django_db
def test_incomplete_donations_remind():
    timestamp = timezone.now() - timedelta(days=REMIND_INCOMPLETE_AFTER_DAYS)
    donor = DonorFactory(email="test@example.com")
    DonationFactory(donor=donor, completed=False, timestamp=timestamp)
    assert len(list(get_incomplete_donations_to_remind())) == 1


@pytest.mark.django_db
def test_incomplete_donations_remind_not_if_donor_donated_after():
    timestamp = timezone.now() - timedelta(days=REMIND_INCOMPLETE_AFTER_DAYS)
    donor = DonorFactory(email="test@example.com")
    DonationFactory(donor=donor, completed=False, timestamp=timestamp)
    DonationFactory(
        donor=donor, completed=True, timestamp=timestamp + timedelta(minutes=1)
    )
    assert len(list(get_incomplete_donations_to_remind())) == 0


@pytest.mark.django_db
def test_incomplete_donations_remind_not_if_email_donated_after():
    timestamp = timezone.now() - timedelta(days=REMIND_INCOMPLETE_AFTER_DAYS)
    donor = DonorFactory(email="test@example.com")
    DonationFactory(donor=donor, completed=False, timestamp=timestamp)
    donor_2 = DonorFactory(email="test@example.com")
    DonationFactory(
        donor=donor_2, completed=True, timestamp=timestamp + timedelta(minutes=1)
    )
    assert len(list(get_incomplete_donations_to_remind())) == 0


@pytest.mark.django_db
def test_incomplete_donations_remind_not_if_email_donated_shortly_before():
    timestamp = timezone.now() - timedelta(days=REMIND_INCOMPLETE_AFTER_DAYS)
    donor = DonorFactory(email="test@example.com")
    DonationFactory(donor=donor, completed=False, timestamp=timestamp)
    DonationFactory(
        donor=donor, completed=True, timestamp=timestamp - timedelta(days=2)
    )
    assert len(list(get_incomplete_donations_to_remind())) == 0


@pytest.mark.django_db
def test_incomplete_donations_ignore_if_spam():
    timestamp = timezone.now() - timedelta(days=REMIND_INCOMPLETE_AFTER_DAYS)
    donor = DonorFactory(email="test@example.com")
    for _ in range(0, DONATION_SPAM_COUNT):
        DonationFactory(donor=donor, completed=False, timestamp=timestamp)
    assert len(list(get_incomplete_donations_to_remind())) == 0


@pytest.mark.django_db
def test_send_incomplete_reminder(mailoutbox):
    timestamp = timezone.now() - timedelta(days=REMIND_INCOMPLETE_AFTER_DAYS)
    donor = DonorFactory(email="test@example.com")
    amount = Decimal("10.00")
    order = Order.objects.create(
        user_email=donor.email,
        total_net=amount,
        total_gross=amount,
        is_donation=True,
    )
    payment = Payment.objects.create(order=order, variant="sepa")
    donation = DonationFactory(
        method="sepa",
        donor=donor,
        completed=False,
        timestamp=timestamp,
        payment=payment,
        order=order,
    )
    send_incomplete_donation_reminder(donation)
    donation.refresh_from_db()
    assert donation.email_sent is not None
    assert INCOMPLETE_DONATION_NOTE in donation.note
    assert donor.email_confirmation_sent is not None

    assert len(mailoutbox) == 1
    m = mailoutbox[0]
    assert settings.SITE_URL + payment.get_absolute_payment_url() in m.body
    assert donor.get_donate_url() in m.body
    assert list(m.to) == [donor.email]
