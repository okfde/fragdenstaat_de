from datetime import timedelta

from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory
from django.urls import reverse
from django.utils import timezone

import pytest
from cms.api import add_plugin
from cms.models import Placeholder

from fragdenstaat_de.fds_donation.cms_plugins import DonationGiftFormPlugin
from fragdenstaat_de.fds_donation.models import (
    Donation,
    DonationGift,
    DonationGiftOrder,
    Donor,
    Recurrence,
)


@pytest.fixture
def donation_gift():
    return DonationGift.objects.create(
        name="Gift",
        category_slug="test",
    )


@pytest.fixture
def donor():
    donor = Donor.objects.create(
        email="test@example.org", email_confirmed=timezone.now()
    )
    Donation.objects.create(donor=donor, amount=10.0, completed=True)
    return donor


@pytest.fixture
def request_with_session():
    request = RequestFactory().get("/")
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    middleware = AuthenticationMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    return request


@pytest.fixture
def donor_client(client, donor):
    url = donor.get_login_url()
    client.post(url)
    yield client
    client.post(reverse("fds_donation:donor-logout"))


@pytest.mark.django_db
def test_order_no_donor(client, donor, donation_gift):
    response = client.post(
        reverse("fds_donation:make_order", kwargs={"category": "test"}),
    )
    assert response.status_code == 302
    assert response.url == reverse("fds_donation:donor-send-login-link")


@pytest.mark.django_db
def test_order(donor_client, donor, donation_gift):
    response = donor_client.post(
        reverse(
            "fds_donation:make_order",
            kwargs={"category": "test"},
        ),
        {
            "next": "/spenden/danke/",
            "chosen_gift": donation_gift.id,
            "shipping_first_name": "Test",
            "shipping_last_name": "User",
            "shipping_address": "Test Street 1",
            "shipping_city": "Test City",
            "shipping_postcode": "12345",
            "shipping_country": "DE",
        },
    )
    assert response.status_code == 302
    assert response.url.startswith("/spenden/danke/")
    order = DonationGiftOrder.objects.get(donation_gift=donation_gift)
    assert order.first_name == "Test"
    assert order.last_name == "User"
    assert order.address == "Test Street 1"
    assert order.city == "Test City"
    assert order.postcode == "12345"
    assert order.country == "DE"
    assert order.email == donor.email
    assert order.donation == donor.donations.last()


@pytest.mark.django_db
def test_order_ineligible_amount(donor_client, donor, donation_gift):
    donation_gift.min_recurring_amount = 20.0
    donation_gift.save()
    response = donor_client.post(
        reverse(
            "fds_donation:make_order",
            kwargs={"category": "test"},
        ),
        {
            "next": "/spenden/danke/",
            "chosen_gift": donation_gift.id,
            "shipping_first_name": "Test",
            "shipping_last_name": "User",
            "shipping_address": "Test Street 1",
            "shipping_city": "Test City",
            "shipping_postcode": "12345",
            "shipping_country": "DE",
        },
        headers={"Referer": "/foo/"},
    )
    assert response.status_code == 302
    assert response.url.startswith("/foo/")

    # Fix it
    donor.recurring_amount = 20
    donor.save()
    response = donor_client.post(
        reverse(
            "fds_donation:make_order",
            kwargs={"category": "test"},
        ),
        {
            "next": "/spenden/danke/",
            "chosen_gift": donation_gift.id,
            "shipping_first_name": "Test",
            "shipping_last_name": "User",
            "shipping_address": "Test Street 1",
            "shipping_city": "Test City",
            "shipping_postcode": "12345",
            "shipping_country": "DE",
        },
        headers={"Referer": "/foo/"},
    )
    assert response.status_code == 302
    assert response.url.startswith("/spenden/danke/")


@pytest.mark.django_db
def test_order_ineligible_streak(donor_client, donor, donation_gift):
    donation_gift.min_streak_months = 11
    donation_gift.save()
    response = donor_client.post(
        reverse(
            "fds_donation:make_order",
            kwargs={"category": "test"},
        ),
        {
            "next": "/spenden/danke/",
            "chosen_gift": donation_gift.id,
            "shipping_first_name": "Test",
            "shipping_last_name": "User",
            "shipping_address": "Test Street 1",
            "shipping_city": "Test City",
            "shipping_postcode": "12345",
            "shipping_country": "DE",
        },
        headers={"Referer": "/foo/"},
    )
    assert response.status_code == 302
    assert response.url.startswith("/foo/")

    # Fix it
    Recurrence.objects.create(
        donor=donor,
        active=True,
        interval=12,
        start_date=timezone.now() - timedelta(days=365),
    )
    response = donor_client.post(
        reverse(
            "fds_donation:make_order",
            kwargs={"category": "test"},
        ),
        {
            "next": "/spenden/danke/",
            "chosen_gift": donation_gift.id,
            "shipping_first_name": "Test",
            "shipping_last_name": "User",
            "shipping_address": "Test Street 1",
            "shipping_city": "Test City",
            "shipping_postcode": "12345",
            "shipping_country": "DE",
        },
        headers={"Referer": "/foo/"},
    )
    assert response.status_code == 302
    assert response.url.startswith("/foo/")


@pytest.mark.django_db
def test_order_no_inventory_left(donor_client, donor, donation_gift):
    donation_gift.inventory = 1
    donation_gift.save()

    DonationGiftOrder.objects.create(donation_gift=donation_gift)

    response = donor_client.post(
        reverse(
            "fds_donation:make_order",
            kwargs={"category": "test"},
        ),
        {
            "next": "/spenden/danke/",
            "chosen_gift": donation_gift.id,
            "shipping_first_name": "Test",
            "shipping_last_name": "User",
            "shipping_address": "Test Street 1",
            "shipping_city": "Test City",
            "shipping_postcode": "12345",
            "shipping_country": "DE",
        },
        headers={"Referer": "/foo/"},
    )
    assert response.status_code == 302
    assert response.url.startswith("/foo/")

    # Fix it:
    DonationGiftOrder.objects.all().delete()

    response = donor_client.post(
        reverse(
            "fds_donation:make_order",
            kwargs={"category": "test"},
        ),
        {
            "next": "/spenden/danke/",
            "chosen_gift": donation_gift.id,
            "shipping_first_name": "Test",
            "shipping_last_name": "User",
            "shipping_address": "Test Street 1",
            "shipping_city": "Test City",
            "shipping_postcode": "12345",
            "shipping_country": "DE",
        },
        headers={"Referer": "/foo/"},
    )
    assert response.status_code == 302
    assert response.url.startswith("/spenden/danke/")


@pytest.mark.django_db
def test_donation_gift_order_plugin_no_donor(request_with_session):
    placeholder = Placeholder.objects.create(slot="test")
    model_instance = add_plugin(
        placeholder,
        DonationGiftFormPlugin,
        "de",
    )
    plugin_instance = model_instance.get_plugin_class_instance()
    context = plugin_instance.render(
        {"request": request_with_session}, model_instance, None
    )
    assert "form" not in context


@pytest.mark.django_db
def test_donation_gift_order_plugin_no_gift(
    request_with_session,
    donor,
):
    request_with_session.session["donor_id"] = donor.id
    request_with_session.session.save()

    placeholder = Placeholder.objects.create(slot="test")
    model_instance = add_plugin(
        placeholder,
        DonationGiftFormPlugin,
        "de",
    )
    model_instance.category = "test"
    model_instance.save()
    plugin_instance = model_instance.get_plugin_class_instance()
    context = plugin_instance.render(
        {"request": request_with_session}, model_instance, None
    )
    assert "form" in context
    assert hasattr(context["form"], "gift_error_message")


@pytest.mark.django_db
def test_donation_gift_order_plugin(request_with_session, donor, donation_gift):
    request_with_session.session["donor_id"] = donor.id
    request_with_session.session.save()

    placeholder = Placeholder.objects.create(slot="test")
    model_instance = add_plugin(
        placeholder,
        DonationGiftFormPlugin,
        "de",
    )
    model_instance.category = "test"
    model_instance.save()
    plugin_instance = model_instance.get_plugin_class_instance()
    context = plugin_instance.render(
        {"request": request_with_session}, model_instance, None
    )
    assert "form" in context
    assert not hasattr(context["form"], "gift_error_message")
    assert context["form"].fields["chosen_gift"].queryset.count() == 1
