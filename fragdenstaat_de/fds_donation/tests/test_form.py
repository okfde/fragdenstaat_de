import base64
import json

import pytest

from ..forms import DonationFormFactory
from ..models import DonationGift


def make_settings(data):
    return base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")


@pytest.mark.django_db
def test_incomplete_donation_gift_shipping_form():
    donation_gift = DonationGift.objects.create(name="Test")
    form_factory = DonationFormFactory()
    form = form_factory.make_form(
        data={
            "amount": "",
            "chosen_gift": str(donation_gift.pk),
            "first_name": "",
            "form_settings": make_settings(
                {
                    "gift_options": [donation_gift.pk],
                    "default_gift": donation_gift.pk,
                }
            ),
            "interval": 12,
            "keyword": "",
            "purpose": "",
            "reference": "",
            "salutation": "informal_m",
        }
    )

    assert not form.is_valid()
