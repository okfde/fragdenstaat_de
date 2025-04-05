import base64
import json

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory

import pytest

from ..forms import DonationFormFactory
from ..models import DonationGift
from .factories import DonationGiftOrderFactory


def make_settings(data):
    return base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")


@pytest.mark.django_db
def test_incomplete_donation_gift_shipping_form():
    donation_gift = DonationGift.objects.create(name="Test")
    form_factory = DonationFormFactory()
    request = RequestFactory().get("/donation/")
    request.user = AnonymousUser()
    form = form_factory.make_form(
        request=request,
        data={
            "amount": "123.45",
            "chosen_gift": str(donation_gift.pk),
            "first_name": "Test",
            "last_name": "Test",
            "email": "test@example.com",
            "form_settings": make_settings(
                {
                    "interval": "once_recurring",
                    "gift_options": [donation_gift.pk],
                    "default_gift": donation_gift.pk,
                }
            ),
            "interval": 12,
            "payment_method": "banktransfer",
            "receipt": "0",
            "contact": "1",
            "account": "0",
            "test": str(3 + 4),
            "keyword": "",
            "purpose": "",
            "reference": "",
            "salutation": "informal_m",
        },
    )
    assert not form.is_valid()
    assert "shipping_address" in form.errors
    assert "shipping_postcode" in form.errors
    assert "shipping_city" in form.errors
    assert "shipping_country" in form.errors


@pytest.mark.django_db
def test_donation_gift_inventory_empty():
    donation_gift = DonationGift.objects.create(name="Test", inventory=1)
    form_factory = DonationFormFactory()
    request = RequestFactory().get("/donation/")
    request.user = AnonymousUser()
    form = form_factory.make_form(
        request=request,
        data={
            "amount": "123.45",
            "chosen_gift": str(donation_gift.pk),
            "first_name": "Test",
            "last_name": "Test",
            "email": "test@example.com",
            "form_settings": make_settings(
                {
                    "interval": "once_recurring",
                    "gift_options": [donation_gift.pk],
                    "default_gift": donation_gift.pk,
                }
            ),
            "interval": 12,
            "payment_method": "banktransfer",
            "receipt": "0",
            "contact": "1",
            "account": "0",
            "shipping_address": "Test",
            "shipping_postcode": "Test",
            "shipping_city": "Test",
            "shipping_country": "DE",
            "test": str(3 + 4),
            "keyword": "",
            "purpose": "",
            "reference": "",
            "salutation": "informal_m",
        },
    )
    # Last one gets ordered
    DonationGiftOrderFactory.create(
        donation_gift=donation_gift,
    )
    assert not form.is_valid()
    assert "chosen_gift" in form.errors


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
