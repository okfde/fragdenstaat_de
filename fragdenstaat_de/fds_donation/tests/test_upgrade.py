from datetime import timedelta

from django.utils import timezone

import pytest

from ..models import Donation, Recurrence


@pytest.mark.django_db
def test_recurrence_should_upgrade(donor):
    not_long_ago = timezone.now() - timedelta(days=10)
    longer_ago = timezone.now() - timedelta(days=120)
    today = timezone.now()

    recurrence = Recurrence.objects.create(
        start_date=today, donor=donor, interval=1, amount=10
    )

    assert recurrence.should_upgrade(0)
    assert not recurrence.should_upgrade(1)
    recurrence.start_date = today - timedelta(days=320)
    recurrence.last_upgrade = today - timedelta(days=5)

    assert recurrence.should_upgrade(3)
    assert not recurrence.should_upgrade(6)

    recurrence.last_upgrade = None
    donation = Donation.objects.create(
        donor=donor,
        amount=10,
        timestamp=not_long_ago,
        completed=True,
        method="sepa",
    )

    assert not recurrence.should_upgrade(20)
    assert not recurrence.should_upgrade(45)

    donation.delete()

    donation = Donation.objects.create(
        donor=donor,
        amount=10,
        timestamp=longer_ago,
        completed=True,
        received_timestamp=longer_ago,
    )

    assert recurrence.should_upgrade(80)
    assert not recurrence.should_upgrade(180)
