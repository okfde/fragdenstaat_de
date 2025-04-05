from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from ..models import Donation, DonationGift, DonationGiftOrder, Donor


class DonorFactory(DjangoModelFactory):
    class Meta:
        model = Donor

    first_name = "Jane"
    last_name = factory.Sequence(lambda n: "D%se" % ("o" * min(20, int(n))))


class DonationFactory(DjangoModelFactory):
    class Meta:
        model = Donation

    donor = factory.SubFactory(DonorFactory)
    amount = Decimal("5.00")
    method = "banktransfer"


class DonationGiftFactory(DjangoModelFactory):
    class Meta:
        model = DonationGift

    name = factory.Sequence(lambda n: "Test Gift %s" % n)
    description = factory.Sequence(lambda n: "Description %s" % n)
    inventory = None


class DonationGiftOrderFactory(DjangoModelFactory):
    class Meta:
        model = DonationGiftOrder

    donation = factory.SubFactory(DonationFactory)
    donation_gift = factory.SubFactory(DonationGiftFactory)
