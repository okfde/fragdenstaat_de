import pytest
from froide_payment.models import Order, Payment
from froide_payment.provider.banktransfer import generate_transfer_code

from ..external import find_donation
from .factories import DonationFactory, DonorFactory


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
