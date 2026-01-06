import pytest
from pytest_factoryboy import register

from .. import models as donation_models
from .factories import DonorFactory

register(DonorFactory)


@pytest.fixture
def unsuspicious(monkeypatch):
    monkeypatch.setattr(
        donation_models, "check_suspicious_request", lambda *args, **kwargs: None
    )
