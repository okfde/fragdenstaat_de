import uuid
from datetime import timedelta

from django.contrib.sites.models import Site
from django.test import Client
from django.utils import timezone

import pytest
from cms import api as cms_api
from djangocms_versioning.models import Version

from fragdenstaat_de.fds_blog.managers import PUBLISHED
from fragdenstaat_de.fds_blog.models import Article, Category

HTTP_HOST = "localhost"


@pytest.fixture(autouse=True)
def _reset_language():
    """Reset the active language after each test to avoid leaking
    thread-local state (e.g. de-ls) into subsequent test modules."""
    from django.utils import translation

    lang = translation.get_language()
    yield
    translation.activate(lang)


def get(client: Client, url: str, **kwargs):
    """GET request with the correct HTTP_HOST so LanguageUtilsMiddleware is active.

    In test settings, DEBUG=False and ALLOWED_HOSTS[0]="localhost", so the
    middleware skips processing unless HTTP_HOST matches "localhost".
    """
    return client.get(url, HTTP_HOST=HTTP_HOST, **kwargs)


def publish_page_content(page, language, user):
    """Publish a page's content for the given language via djangocms-versioning."""
    content = page.pagecontent_set(manager="_original_manager").get(language=language)
    version = Version.objects.get_for_content(content)
    version.publish(user)


def add_language_to_page(page, language, title, user, publish=True, **kwargs):
    """Add a language translation to an existing page, optionally publishing it."""
    cms_api.create_page_content(language, title, page, created_by=user, **kwargs)
    if publish:
        publish_page_content(page, language, user)


@pytest.fixture
def admin_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="admin"
    )


@pytest.fixture
def cms_page(admin_user):
    """Factory: creates published CMS pages, cleans up after the test."""
    from cms.appresolver import clear_app_resolvers, get_app_patterns

    pages = []

    def _create(title, language, **kwargs):
        page = cms_api.create_page(
            title, "cms/page.html", language, created_by=admin_user, **kwargs
        )
        publish_page_content(page, language, admin_user)
        pages.append(page)
        if kwargs.get("apphook"):
            clear_app_resolvers()
            get_app_patterns()
        return page

    yield _create

    has_apphook = any(p.application_urls for p in pages)
    for page in reversed(pages):
        page.delete()
    if has_apphook:
        clear_app_resolvers()


@pytest.fixture
def blog_page(cms_page, admin_user):
    """CMS page with the blog apphook, published in de and de-ls.

    The explicit blog URL in tests/urls.py provides reverse() support.
    This CMS apphook page ensures CurrentPageMiddleware sets
    request.current_page, so LanguageUtilsMiddleware does not redirect
    blog URLs — matching production behaviour.

    After creating the page we re-populate the global APP_RESOLVERS so
    that applications_page_check() can find the apphook page (it is
    normally populated at cms.urls import time, before any test data exists).

    """
    from cms.appresolver import clear_app_resolvers, get_app_patterns

    page = cms_page(
        "Blog", "de", slug="blog", apphook="FdsBlogApp", apphook_namespace="blog"
    )
    add_language_to_page(page, "de-ls", "Blog", admin_user, slug="blog")

    # Refresh resolvers after adding the de-ls translation.
    clear_app_resolvers()
    get_app_patterns()

    return page


@pytest.fixture
def crowdfunding_page(cms_page):
    """CMS apphook page for crowdfunding, published in de only (no de-ls)."""
    return cms_page(
        "Crowdfunding",
        "de",
        slug="crowdfunding",
        apphook="CrowdfundingCMSApp",
        apphook_namespace="crowdfunding",
    )


def create_article(
    language, category, title="Test Article", slug="test-article", **kwargs
):
    """Create a published blog article linked to the current site."""
    defaults = {
        "title": title,
        "slug": slug,
        "language": language,
        "status": PUBLISHED,
        "start_publication": timezone.now() - timedelta(hours=1),
    }
    defaults.update(kwargs)
    article = Article.objects.create(**defaults)
    article.categories.add(category)
    article.sites.add(Site.objects.get_current())
    return article


@pytest.fixture
def category_de(db):
    """A blog category with a German translation."""
    cat = Category.objects.create(order=0)
    cat.set_current_language("de")
    cat.title = "Nachrichten"
    cat.slug = "nachrichten"
    cat.save()
    return cat


@pytest.fixture
def category_de_ls(category_de):
    """Extend the German category with a de-ls translation."""
    category_de.set_current_language("de-ls")
    category_de.title = "Nachrichten"
    category_de.slug = "nachrichten"
    category_de.save()
    return category_de


@pytest.mark.django_db
class TestEasyLanguageRedirect:
    """Tests what happens when navigating to /de-ls/... directly.

    Non-CMS pages should be redirected to the default language equivalent.
    CMS pages with a de-ls translation should render; without one they redirect.
    Admin URLs are exempt from redirection.
    """

    # --- Non-CMS ---

    def test_non_cms_redirects(self, client):
        response = get(client, "/de-ls/account/login/")
        assert response.status_code == 301
        assert response["Location"] == "/account/login/"

    def test_non_cms_preserves_query_string(self, client):
        response = get(client, "/de-ls/account/login/", QUERY_STRING="next=/")
        assert response.status_code == 301
        assert response["Location"] == "/account/login/?next=/"

    def test_non_cms_post_not_redirected(self, client):
        """POST requests to /de-ls/ are not redirected (middleware only handles GET)."""
        response = client.post("/de-ls/account/login/", HTTP_HOST=HTTP_HOST)
        assert response.status_code != 301

    def test_non_cms_de_not_redirected(self, client):
        response = get(client, "/account/login/")
        assert response.status_code != 301

    # --- Admin (exception) ---

    def test_admin_not_redirected(self, client, admin_user):
        client.force_login(admin_user)
        response = get(client, "/de-ls/admin/")
        assert response.status_code == 200

    def test_admin_subpage_not_redirected(self, client, admin_user):
        client.force_login(admin_user)
        response = get(client, "/de-ls/admin/fds_blog/article/")
        assert response.status_code == 200

    # --- Plain CMS page ---

    def test_cms_page_with_translation(self, client, admin_user, cms_page):
        page = cms_page("Testseite", "de")
        add_language_to_page(page, "de-ls", "Testseite Leicht", admin_user)

        de_ls_url = page.get_absolute_url("de-ls")
        response = get(client, de_ls_url)
        assert response.status_code == 200

    def test_cms_page_with_unpublished_translation(self, client, admin_user, cms_page):
        """An unpublished de-ls translation should behave like no translation."""
        page = cms_page("Testseite", "de")
        add_language_to_page(
            page, "de-ls", "Testseite Leicht", admin_user, publish=False
        )

        de_url = page.get_absolute_url("de")
        de_ls_url = f"/de-ls{de_url}"
        response = get(client, de_ls_url)
        assert response.status_code == 302
        assert de_url in response["Location"]

    def test_cms_page_without_translation(self, client, cms_page):
        page = cms_page("Testseite", "de")

        de_url = page.get_absolute_url("de")
        de_ls_url = f"/de-ls{de_url}"
        response = get(client, de_ls_url)

        assert response.status_code == 302
        assert de_url in response["Location"]

    def test_cms_page_de_not_redirected(self, client, cms_page):
        page = cms_page("Testseite", "de")

        de_url = page.get_absolute_url("de")
        response = get(client, de_url)
        assert response.status_code == 200

    # --- CMS apphook page ---

    def test_apphook_with_translation(self, client, blog_page):
        de_ls_url = blog_page.get_absolute_url("de-ls")
        response = get(client, de_ls_url)
        assert response.status_code == 200

    def test_apphook_without_translation(self, client, crowdfunding_page):
        de_url = crowdfunding_page.get_absolute_url("de")
        de_ls_url = f"/de-ls{de_url}"
        response = get(client, de_ls_url)
        assert response.status_code == 302
        assert de_url in response["Location"]

    def test_apphook_de_not_redirected(self, client, blog_page):
        de_url = blog_page.get_absolute_url("de")
        response = get(client, de_url)
        assert response.status_code == 200

    # --- Blog article ---

    def test_blog_de_article_accessible(self, client, category_de):
        article = create_article("de", category_de)
        response = get(client, article.get_absolute_url())
        assert response.status_code == 200

    def test_blog_de_ls_article_accessible(self, client, blog_page, category_de_ls):
        article = create_article("de-ls", category_de_ls)
        response = get(client, article.get_absolute_url())
        assert response.status_code == 200

    def test_blog_de_article_not_found_via_de_ls(self, client, blog_page, category_de):
        """A de-only article is not accessible under /de-ls/ (different slug → 404)."""
        article = create_article("de", category_de)
        de_url = article.get_absolute_url()
        de_ls_url = f"/de-ls{de_url}"
        response = get(client, de_ls_url)
        assert response.status_code == 404


@pytest.mark.django_db
class TestEasylangToggle:
    """Tests `easylang_toggle` template tag output.

    The tag should set has_translation=True only when the CMS page has
    published content in the target language. For non-CMS pages
    (no current_page), has_translation is always False.
    """

    def _get_toggle_context(self, client, url):
        """Make a real GET request, then call the tag function with request context."""
        from django.template import Context

        from fragdenstaat_de.fds_easylang.templatetags.easylang_tags import (
            easylang_toggle,
        )

        response = get(client, url)
        request = response.wsgi_request
        context = Context({"request": request, "view": None})
        return easylang_toggle(context)

    # --- Non-CMS page (no current_page → always False) ---

    def test_non_cms_no_translation_from_de(self, client):
        ctx = self._get_toggle_context(client, "/account/login/")
        assert not ctx["has_translation"]
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["home_url"] == "/de-ls/"

    def test_non_cms_no_translation_from_de_ls(self, client):
        """de-ls non-CMS URLs redirect, so we check the redirected response."""
        response = get(client, "/de-ls/account/login/")
        assert response.status_code == 301
        ctx = self._get_toggle_context(client, response["Location"])
        assert not ctx["has_translation"]
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"

    # --- Plain CMS page ---

    def test_cms_page_with_translation_from_de(self, client, admin_user, cms_page):
        page = cms_page("Testseite", "de")
        add_language_to_page(page, "de-ls", "Testseite Leicht", admin_user)

        ctx = self._get_toggle_context(client, page.get_absolute_url("de"))
        assert ctx["has_translation"] is True
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == page.get_absolute_url("de-ls")
        assert ctx["home_url"] == "/de-ls/"

    def test_cms_page_with_translation_from_de_ls(self, client, admin_user, cms_page):
        page = cms_page("Testseite", "de")
        add_language_to_page(page, "de-ls", "Testseite Leicht", admin_user)

        ctx = self._get_toggle_context(client, page.get_absolute_url("de-ls"))
        assert ctx["has_translation"] is True
        assert ctx["current_language"] == "de-ls"
        assert ctx["target_language"] == "de"
        assert ctx["target_url"] == page.get_absolute_url("de")
        assert ctx["home_url"] == "/de/"

    @pytest.mark.xfail(
        reason="page.get_urls() includes draft content, so toggle shows link to unpublished page"
    )
    def test_cms_page_with_unpublished_translation(self, client, admin_user, cms_page):
        """An unpublished de-ls translation should not count as available."""
        page = cms_page("Testseite", "de")
        add_language_to_page(
            page, "de-ls", "Testseite Leicht", admin_user, publish=False
        )

        ctx = self._get_toggle_context(client, page.get_absolute_url("de"))
        assert not ctx["has_translation"]

    def test_cms_page_without_translation(self, client, cms_page):
        page = cms_page("Testseite", "de")

        ctx = self._get_toggle_context(client, page.get_absolute_url("de"))
        assert not ctx["has_translation"]
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"

    # --- CMS apphook page ---

    def test_apphook_with_translation_from_de(self, client, blog_page):
        ctx = self._get_toggle_context(client, blog_page.get_absolute_url("de"))
        assert ctx["has_translation"] is True
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == blog_page.get_absolute_url("de-ls")

    def test_apphook_with_translation_from_de_ls(self, client, blog_page):
        ctx = self._get_toggle_context(client, blog_page.get_absolute_url("de-ls"))
        assert ctx["has_translation"] is True
        assert ctx["current_language"] == "de-ls"
        assert ctx["target_language"] == "de"
        assert ctx["target_url"] == blog_page.get_absolute_url("de")

    @pytest.mark.xfail
    def test_apphook_without_translation(self, client, crowdfunding_page):
        """CMS apphook page without de-ls: toggle should show modal."""
        ctx = self._get_toggle_context(client, crowdfunding_page.get_absolute_url("de"))
        assert not ctx["has_translation"]

    # --- Blog article ---

    def test_blog_with_translation_from_de(self, client, blog_page, category_de_ls):
        """Two articles linked by uuid — toggle should detect the translation."""
        shared_uuid = uuid.uuid4()
        de_article = create_article(
            "de", category_de_ls, title="German", uuid=shared_uuid
        )
        create_article("de-ls", category_de_ls, title="Easy", uuid=shared_uuid)

        ctx = self._get_toggle_context(client, de_article.get_absolute_url())
        assert ctx["has_translation"] is True
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"

    def test_blog_with_translation_from_de_ls(self, client, blog_page, category_de_ls):
        """Toggle from de-ls article should point back to de."""
        shared_uuid = uuid.uuid4()
        create_article("de", category_de_ls, title="German", uuid=shared_uuid)
        de_ls_article = create_article(
            "de-ls", category_de_ls, title="Easy", uuid=shared_uuid
        )

        ctx = self._get_toggle_context(client, de_ls_article.get_absolute_url())
        assert ctx["has_translation"] is True
        assert ctx["current_language"] == "de-ls"
        assert ctx["target_language"] == "de"

    @pytest.mark.xfail(reason="toggle checks current_page, not article translations")
    def test_blog_without_translation(self, client, blog_page, category_de):
        """Single de article, no translation — toggle should show modal."""
        article = create_article("de", category_de)

        ctx = self._get_toggle_context(client, article.get_absolute_url())
        assert not ctx["has_translation"]
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
