import pytest

from froide.account.factories import UserFactory


@pytest.fixture
def dummy_user():
    yield UserFactory(username="dummy")


@pytest.fixture()
def request_throttle_settings(settings):
    froide_config = settings.FROIDE_CONFIG
    froide_config["request_throttle"] = [(2, 60), (5, 60 * 60)]
    settings.FROIDE_CONFIG = froide_config


@pytest.fixture()
def page(browser):
    context = browser.new_context(locale="en")
    page = context.new_page()
    yield page
    page.close()
