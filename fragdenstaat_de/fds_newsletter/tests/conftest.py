import pytest

from ..models import Newsletter


@pytest.fixture
def newsletter():
    """Fixture to create a newsletter."""
    return Newsletter.objects.create(
        title="Test Newsletter",
        slug="test-newsletter",
        description="Test description",
    )
