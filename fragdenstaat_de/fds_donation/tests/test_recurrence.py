from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

import pytest
from dateutil.relativedelta import relativedelta

from ..models import Donation, Donor, Recurrence
from ..recurrence import (
    check_late_recurring_donors,
    get_late_recurrences,
    process_recurrence_on_donor,
)
from ..services import merge_donor_list
from .factories import DonorFactory, make_banktransfer_donation


@pytest.mark.django_db
def test_banktransfer_just_created():
    donor = DonorFactory.create()
    now = timezone.now()
    first_date = now
    amount = Decimal("10.00")
    donation = make_banktransfer_donation(donor, amount, first_date)

    process_recurrence_on_donor(donor)

    donation.refresh_from_db()
    recurrence = donation.recurrence
    assert recurrence is not None
    assert recurrence.method == "banktransfer"
    assert recurrence.amount == amount
    assert recurrence.start_date == donation.order.subscription.created
    assert recurrence.active is False
    assert recurrence.cancel_date is None


@pytest.mark.django_db
def test_banktransfer_first_never_received_after_a_month_and_a_bit():
    donor = DonorFactory.create()
    now = timezone.now()
    # Known until date + generous buffer before
    first_date = now - timedelta(days=14) - relativedelta(day=1) - timedelta(days=15)
    amount = Decimal("10.00")
    donation = make_banktransfer_donation(donor, amount, first_date)

    process_recurrence_on_donor(donor)

    donation.refresh_from_db()
    recurrence = donation.recurrence
    assert recurrence is not None
    assert recurrence.method == "banktransfer"
    assert recurrence.amount == amount
    assert recurrence.start_date == donation.order.subscription.created
    assert recurrence.active is False
    assert recurrence.cancel_date is not None
    assert recurrence.cancel_date.date() == first_date.date()


@pytest.mark.django_db
def test_banktransfer_first_received():
    donor = DonorFactory.create()
    now = timezone.now()
    first_date = now - relativedelta(months=1) - timedelta(days=5)
    amount = Decimal("10.00")
    donation = make_banktransfer_donation(donor, amount, first_date)
    donation.received_timestamp = donation.timestamp + timedelta(days=2)
    donation.save()

    process_recurrence_on_donor(donor)

    donation.refresh_from_db()
    recurrence = donation.recurrence
    assert recurrence is not None
    assert recurrence.method == "banktransfer"
    assert recurrence.amount == amount
    assert recurrence.start_date == donation.order.subscription.created
    assert recurrence.active is True
    assert recurrence.cancel_date is None


@pytest.mark.django_db
def test_banktransfer_first_received_next_missed():
    donor = DonorFactory.create()
    now = timezone.now()
    first_date = now - relativedelta(months=3) - timedelta(days=5)
    amount = Decimal("10.00")
    donation = make_banktransfer_donation(donor, amount, first_date)
    donation.received_timestamp = donation.timestamp + timedelta(days=2)
    donation.amount_received = amount
    donation.save()

    process_recurrence_on_donor(donor)

    donation.refresh_from_db()
    recurrence = donation.recurrence
    assert recurrence is not None
    assert recurrence.method == "banktransfer"
    assert recurrence.amount == amount
    assert recurrence.start_date == donation.order.subscription.created
    assert recurrence.active is True
    assert recurrence.cancel_date is not None
    assert recurrence.cancel_date.date() == donation.received_timestamp.date()


@pytest.mark.django_db
def test_banktransfer_imported():
    donor = DonorFactory.create()
    now = timezone.now()
    first_date = now - relativedelta(months=2)
    amount = Decimal("10.00")
    first_donation = Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=first_date,
        received_timestamp=first_date,
        completed=True,
    )
    second_date = now - relativedelta(months=1)
    second_donation = Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=second_date,
        received_timestamp=second_date,
        completed=True,
    )

    process_recurrence_on_donor(donor)
    first_donation.refresh_from_db()
    second_donation.refresh_from_db()
    recurrence = second_donation.recurrence
    assert recurrence is not None
    assert first_donation.recurrence is not None
    assert first_donation.recurrence == recurrence
    assert recurrence.method == "banktransfer"
    assert recurrence.amount == amount
    assert recurrence.start_date == first_donation.timestamp
    assert recurrence.active is True
    assert recurrence.cancel_date is None


@pytest.mark.django_db
def test_banktransfer_imported_canceled():
    donor = DonorFactory.create()
    now = timezone.now()
    first_date = now - relativedelta(months=4)
    amount = Decimal("10.00")
    first_donation = Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=first_date,
        received_timestamp=first_date,
        completed=True,
    )
    second_date = now - relativedelta(months=3)
    second_donation = Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=second_date,
        received_timestamp=second_date,
        completed=True,
    )

    process_recurrence_on_donor(donor)

    first_donation.refresh_from_db()
    second_donation.refresh_from_db()
    recurrence = second_donation.recurrence
    assert recurrence is not None
    assert first_donation.recurrence is not None
    assert first_donation.recurrence == recurrence
    assert recurrence.method == "banktransfer"
    assert recurrence.amount == amount
    assert recurrence.start_date == first_donation.timestamp
    assert recurrence.active is True
    assert recurrence.cancel_date is not None
    assert recurrence.cancel_date.date() == second_donation.received_timestamp.date()


@pytest.mark.django_db
def test_banktransfer_add_existing_recurrence():
    donor = DonorFactory.create()
    now = timezone.now().replace(day=15)
    first_date = now - relativedelta(months=3)
    amount = Decimal("10.00")
    first_donation = Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=first_date,
        received_timestamp=first_date,
        completed=True,
    )
    second_date = now - relativedelta(months=2)
    second_donation = Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=second_date,
        received_timestamp=second_date,
        completed=True,
    )
    process_recurrence_on_donor(donor, current_date=now)
    first_donation.refresh_from_db()
    second_donation.refresh_from_db()
    recurrence = second_donation.recurrence
    assert recurrence is not None
    assert recurrence.cancel_date is not None

    last_date = now - relativedelta(months=1)
    last_donation = Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=last_date,
        received_timestamp=last_date,
        completed=True,
    )

    process_recurrence_on_donor(donor, current_date=now)
    last_donation.refresh_from_db()
    recurrence.refresh_from_db()
    assert recurrence == last_donation.recurrence
    assert recurrence.cancel_date is None


@pytest.mark.django_db
@pytest.mark.django_db(transaction=True)
def test_donor_merge():
    now = timezone.now()
    first_date = now - relativedelta(months=4)
    amount = Decimal("10.00")
    donor_1 = DonorFactory.create()
    Donation.objects.create(
        donor=donor_1,
        method="banktransfer",
        amount=amount,
        timestamp=first_date,
        received_timestamp=first_date,
        completed=True,
    )
    second_date = now - relativedelta(months=3)
    second_donation = Donation.objects.create(
        donor=donor_1,
        method="banktransfer",
        amount=amount,
        timestamp=second_date,
        received_timestamp=second_date,
        completed=True,
    )

    process_recurrence_on_donor(donor_1)
    second_donation.refresh_from_db()
    assert second_donation.recurrence is not None
    assert second_donation.recurrence.cancel_date is not None

    first_date_2 = now - relativedelta(months=2)
    donor_2 = DonorFactory.create()
    Donation.objects.create(
        donor=donor_2,
        method="banktransfer",
        amount=amount,
        timestamp=first_date_2,
        received_timestamp=first_date_2,
        completed=True,
    )
    second_date_2 = now - relativedelta(months=1)
    second_donation_2 = Donation.objects.create(
        donor=donor_2,
        method="banktransfer",
        amount=amount,
        timestamp=second_date_2,
        received_timestamp=second_date_2,
        completed=True,
    )

    process_recurrence_on_donor(donor_2)
    second_donation_2.refresh_from_db()
    recurrence = second_donation_2.recurrence
    assert recurrence is not None
    assert recurrence.cancel_date is None

    merge_donor_list([donor_1, donor_2])

    with pytest.raises(Donor.DoesNotExist):
        donor_2.refresh_from_db()

    donor_1.refresh_from_db()
    second_donation.refresh_from_db()
    second_donation_2.refresh_from_db()
    assert second_donation_2.donor == donor_1
    recurrence = second_donation.recurrence
    recurrence.refresh_from_db()
    second_donation_2.recurrence.refresh_from_db()
    assert recurrence == second_donation_2.recurrence
    assert recurrence.cancel_date is None


@pytest.mark.django_db
def test_late_recurrence_check():
    now = timezone.now()
    amount = Decimal("10.00")
    first_date = now + relativedelta(day=31) - relativedelta(months=5)
    donor = DonorFactory.create()
    recurrence = Recurrence.objects.create(
        donor=donor,
        method="banktransfer",
        interval=1,
        amount=amount,
        start_date=first_date,
        active=True,
    )
    Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=first_date,
        received_timestamp=first_date,
        completed=True,
        recurrence=recurrence,
    )
    second_date = first_date + relativedelta(months=1)
    Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=second_date,
        received_timestamp=second_date,
        completed=True,
        recurrence=recurrence,
    )

    late_recurrences = get_late_recurrences()
    assert len(late_recurrences) == 1
    assert late_recurrences[0] == recurrence

    check_late_recurring_donors()

    recurrence.refresh_from_db()
    assert recurrence.cancel_date is not None
    assert recurrence.cancel_date.date() == second_date.date()


@pytest.mark.django_db
def test_breaking_recurrence():
    now = timezone.now()
    amount = Decimal("10.00")
    first_date = now - relativedelta(months=4)
    donor = DonorFactory.create()
    Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=first_date,
        received_timestamp=first_date,
        completed=True,
    )
    second_date = now - relativedelta(months=3)
    Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=second_date,
        received_timestamp=second_date,
        completed=True,
    )

    last_date = now - relativedelta(months=1)
    last_donation = Donation.objects.create(
        donor=donor,
        method="banktransfer",
        amount=amount,
        timestamp=last_date,
        received_timestamp=last_date,
        completed=True,
    )

    process_recurrence_on_donor(donor)

    recurrence = Recurrence.objects.get(donor=donor)
    assert recurrence.cancel_date is not None
    assert recurrence.donations.all().count() == 2
    last_donation.refresh_from_db()
    assert last_donation.recurrence is None


def setup_recurrences(
    streaks: list[tuple[int, int | None]],
) -> Donor:
    donor = DonorFactory.create()
    now = timezone.now()
    amount = Decimal("10.00")
    for start, end in streaks:
        start_date = now - relativedelta(months=24) + relativedelta(months=start)
        end_date = None
        if end is not None:
            end_date = now - relativedelta(months=24) + relativedelta(months=end)
        Recurrence.objects.create(
            donor=donor,
            method="banktransfer",
            interval=1,
            amount=amount,
            start_date=start_date,
            cancel_date=end_date,
            active=True,
        )
    return donor


@pytest.mark.django_db
@pytest.mark.parametrize(
    "streaks, expected",
    [
        ([(0, None)], 0),
        ([(0, 1)], None),
        ([(0, 2), (1, None)], 0),
        ([(0, 2), (2, None)], 0),
        ([(0, 2), (3, None)], 0),
        ([(0, 2), (3, 5)], None),
        ([(0, 2), (4, None)], 1),
        ([(0, 2), (4, 6), (6, 8)], None),
        ([(0, 2), (4, 6), (6, None)], 1),
    ],
)
def test_recurrence_streak_date(streaks, expected):
    donor = setup_recurrences(streaks)
    date = donor.get_recurrence_streak_start_date()
    if expected is None:
        expected_date = None
    else:
        expected_date = (
            donor.recurrences.all().order_by("start_date")[expected].start_date
        )
    assert date == expected_date
