from django.contrib.auth import get_user_model

import pytest
from cms import api as cms_api

from fragdenstaat_de.tests.utils import publish_page_content, reload_urls


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="admin"
    )


@pytest.fixture
def cms_page(admin_user):
    """Factory: creates published CMS pages, cleans up after the test."""
    pages = []

    def _create(title, language, **kwargs):
        page = cms_api.create_page(
            title, "cms/page.html", language, created_by=admin_user, **kwargs
        )
        publish_page_content(page, language, admin_user)
        pages.append(page)
        if kwargs.get("apphook"):
            reload_urls()
        return page

    yield _create

    has_apphook = any(p.application_urls for p in pages)
    for page in reversed(pages):
        page.delete()
    if has_apphook:
        reload_urls()
