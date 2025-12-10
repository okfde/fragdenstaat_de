import base64
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

import pytest

from .. import models as donation_models
from ..form_settings import DonationFormFactory, DonationSettingsForm
from ..models import ONCE, RECURRING, Donation, DonationFormViewCount, DonationGift
from .factories import DonationGiftOrderFactory

User = get_user_model()


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


@pytest.mark.django_db
def test_donation_form_authenticated_user():
    user = User.objects.create_user(username="testuser", email="test@example.com")
    request = RequestFactory().get("/donation/")
    request.user = user
    settings_form = DonationSettingsForm(data={})
    form = settings_form.make_donation_form(request=request, user=user)

    assert form.fields["email"].initial == user.email
    assert form.fields["first_name"].initial == user.first_name
    assert form.fields["last_name"].initial == user.last_name
    assert "account" not in form.fields


@pytest.mark.django_db
def test_donation_form_unauthenticated_user():
    request = RequestFactory().get("/donation/")
    request.user = AnonymousUser()
    settings_form = DonationSettingsForm(data={})
    form = settings_form.make_donation_form(request=request, user=request.user)

    assert "account" in form.fields
    assert form.fields["account"].choices
    assert form.fields["account"].choices


@pytest.mark.django_db
def test_donation_form_interval_choices():
    request = RequestFactory().get("/donation/")
    request.user = AnonymousUser()

    settings_form = DonationSettingsForm(data={})
    form = settings_form.make_donation_form(request=request, user=request.user)
    assert [x[0] for x in form.fields["interval"].choices] == [0, 1, 3, 12]

    form_settings = {
        "interval_choices": "0,1,3",
    }
    settings_form = DonationSettingsForm(data=form_settings)
    form = settings_form.make_donation_form(request=request, user=request.user)
    assert [x[0] for x in form.fields["interval"].choices] == [0, 1, 3]

    form_settings = {
        "interval": ONCE,
        "interval_choices": "0,1,3",
    }
    settings_form = DonationSettingsForm(data=form_settings)
    form = settings_form.make_donation_form(request=request, user=request.user)
    assert [x[0] for x in form.fields["interval"].choices] == [0]
    assert form.fields["interval"].widget.is_hidden

    form_settings = {
        "interval": RECURRING,
        "interval_choices": "0,1,3",
    }
    settings_form = DonationSettingsForm(data=form_settings)
    form = settings_form.make_donation_form(request=request, user=request.user)
    assert [x[0] for x in form.fields["interval"].choices] == [1, 3]
    assert not form.fields["interval"].widget.is_hidden

    form_settings = {
        "interval": RECURRING,
        "interval_choices": "1",
    }
    settings_form = DonationSettingsForm(data=form_settings)
    form = settings_form.make_donation_form(request=request, user=request.user)
    assert [x[0] for x in form.fields["interval"].choices] == [1]
    assert form.fields["interval"].widget.is_hidden


@pytest.mark.django_db
def test_donation_form_hide_purpose():
    request = RequestFactory().get("/donation/")
    request.user = AnonymousUser()

    settings_form = DonationSettingsForm(data={})
    form = settings_form.make_donation_form(request=request, user=request.user)
    assert form.fields["purpose"].widget.is_hidden

    form_settings = {
        "interval_choices": "0,1,3",
        "purpose": "test",
    }
    settings_form = DonationSettingsForm(data=form_settings)
    form = settings_form.make_donation_form(request=request, user=request.user)
    assert form.fields["purpose"].widget.is_hidden

    form_settings = {
        "interval_choices": "0,1,3",
        "purpose": "test,test2",
    }
    settings_form = DonationSettingsForm(data=form_settings)
    form = settings_form.make_donation_form(request=request, user=request.user)
    assert not form.fields["purpose"].widget.is_hidden

    form_settings = {
        "interval_choices": "1,3",
        "purpose": "test,test2",
    }
    settings_form = DonationSettingsForm(data=form_settings)
    form = settings_form.make_donation_form(request=request, user=request.user)
    assert form.fields["purpose"].widget.is_hidden

    form_settings = {
        "interval_choices": "1,3",
        "purpose": "",
    }
    settings_form = DonationSettingsForm(data=form_settings)
    form = settings_form.make_donation_form(request=request, user=request.user)
    assert form.fields["purpose"].widget.is_hidden


@pytest.fixture
def unsuspicious(monkeypatch):
    monkeypatch.setattr(
        donation_models, "check_suspicious_request", lambda *args, **kwargs: None
    )


@pytest.mark.django_db
def test_form_view_counting(client, unsuspicious):
    assert DonationFormViewCount.objects.count() == 0

    path = reverse("fds_donation:donate")
    response = client.get(path)
    assert response.status_code == 200
    view_count = DonationFormViewCount.objects.all().first()

    assert view_count is not None
    assert view_count.count == 1
    assert view_count.path == path
    assert view_count.reference == ""
    assert view_count.date == timezone.now().date()

    response = client.get(path)
    assert response.status_code == 200

    assert DonationFormViewCount.objects.count() == 1
    view_count = DonationFormViewCount.objects.all().first()
    assert view_count.count == 2
    assert view_count.path == path


@pytest.mark.django_db
def test_form_view_counting_reference(client, unsuspicious):
    path = reverse("fds_donation:donate")
    response = client.get(path + "?pk_campaign=mailing-1")
    assert response.status_code == 200
    view_count = DonationFormViewCount.objects.all().first()
    assert view_count is not None
    assert view_count.count == 1
    assert view_count.path == path
    assert view_count.reference == "mailing-1"
    assert view_count.date == timezone.now().date()


@pytest.mark.django_db
def test_quick_donation(client, unsuspicious):
    path = reverse("fds_donation:donate")
    email = "testing@example.com"

    def post():
        return client.post(
            path,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json",
            },
            data={
                "amount": "15.00",
                "interval": "0",
                "first_name": "John",
                "last_name": "Doe",
                "email": email,
            },
        )

    response = post()
    donation = Donation.objects.get(donor__email=email)
    assert donation.amount == 15.00
    assert donation.completed is False
    for _ in range(3):
        response = post()
        assert response.status_code == 200
    # Spam protection kicks in
    response = post()
    assert response.status_code == 400
