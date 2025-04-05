import base64
import json

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory

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


@pytest.mark.django_db
def test_donation_form_track_data():
    form_factory = DonationFormFactory(reference="a", keyword="b", purpose="c")
    request = RequestFactory().get("/donation/")
    request.user = AnonymousUser()
    form = form_factory.make_form(
        request=request,
    )
    assert form.fields["form_url"].initial == "/donation/"

    html = render_to_string(
        "fds_donation/forms/_donation_form.html",
        {"form": form, "request": request},
    )
    assert '''input type="hidden" name="form_url" value="/donation/"''' in html
    assert '''input type="hidden" name="reference" value="a"''' in html
    assert '''input type="hidden" name="keyword" value="b"''' in html
    assert '''input type="hidden" name="purpose" value="c"''' in html
