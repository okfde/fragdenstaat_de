import pytest
from cms.models import Page

from fragdenstaat_de.tests.utils import reload_urls


@pytest.fixture
def search_page(cms_page):
    return cms_page(
        "Suche",
        "de",
        slug="suche",
        apphook="FdsCmsSearchApp",
        apphook_namespace="fds_cms",
    )


def search_option(page):
    return f'<option value="{page.get_absolute_url("de")}">'


@pytest.mark.django_db
class TestCmsSearchRegistry:
    def test_search_page_listed(self, client, search_page):
        response = client.get("/account/login/")
        assert response.status_code == 200
        assert search_option(search_page) in response.content.decode()

    def test_deleted_search_page_not_listed(self, client, search_page):
        option = search_option(search_page)
        Page.objects.get(pk=search_page.pk).delete()
        reload_urls()

        response = client.get("/account/login/")
        assert response.status_code == 200
        assert option not in response.content.decode()

    def test_page_without_search_apphook_not_listed(self, client, search_page):
        search_page.application_urls = ""
        search_page.application_namespace = None
        search_page.save()
        reload_urls()

        response = client.get("/account/login/")
        assert response.status_code == 200
        assert search_option(search_page) not in response.content.decode()
