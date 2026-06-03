import pytest
from pytest_factoryboy import register

from froide.account.factories import UserFactory

from .. import models as donation_models
from .factories import DonorFactory

register(DonorFactory)


@pytest.fixture
def unsuspicious(monkeypatch):
    monkeypatch.setattr(
        donation_models, "check_suspicious_request", lambda *args, **kwargs: None
    )


@pytest.fixture
def dummy_user():
    yield UserFactory(username="dummy")
