import pytest

from ..models import DonationGift, DonationGiftOrder


@pytest.fixture
def limited_donation_gift():
    return DonationGift.objects.create(
        name="Test Gift",
        inventory=3,
    )


@pytest.mark.django_db
def test_order_inventory_warning(mailoutbox, limited_donation_gift):
    DonationGiftOrder.objects.create(donation_gift=limited_donation_gift)
    assert len(mailoutbox) == 0

    # Crossing 5 percent threshold
    DonationGiftOrder.objects.create(donation_gift=limited_donation_gift)
    assert len(mailoutbox) == 1
