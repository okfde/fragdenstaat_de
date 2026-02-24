import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import Client
from django.utils import timezone, translation

import pytest
from cms import api as cms_api
from cms.appresolver import clear_app_resolvers, get_app_patterns
from djangocms_versioning.models import Version

from fragdenstaat_de.fds_blog.managers import PUBLISHED
from fragdenstaat_de.fds_blog.models import Article, Category
from fragdenstaat_de.fds_blog.views import ArticleDetailView, BaseBlogView
from fragdenstaat_de.fds_events.models import Event

HTTP_HOST = "localhost"

# Parameter combinations for tests gated by EASYLANG_ENABLED + staff status.
# Only boundary cases: enabled (anyone through), disabled+anonymous (blocked),
# disabled+staff (through).
# (easylang_enabled, user_fixture, expected_status)
EASYLANG_GATE_PARAMS = [
    (True, None, 200),
    (False, None, 404),
    (False, "staff_user", 200),
]
EASYLANG_GATE_IDS = [
    "enabled-anonymous",
    "disabled-anonymous",
    "disabled-staff",
]


@pytest.fixture(autouse=True)
def _reset_language():
    """Reset the active language after each test to avoid leaking
    thread-local state (e.g. de-ls) into subsequent test modules."""
    lang = translation.get_language()
    yield
    translation.activate(lang)


@pytest.fixture
def easylang_enabled(request, settings):
    """Set EASYLANG_ENABLED and sync the CMS `public` flag for de-ls.

    django-configurations evaluates the `CMS_LANGUAGES` property once at
    startup, so the `public` value for de-ls is baked in.  Changing
    `settings.EASYLANG_ENABLED` alone leaves the CMS cache stale.
    This fixture updates both and clears the CMS cache.

    Use via `indirect=True`:
        @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    """
    from cms.utils.conf import VERIFIED

    value = request.param
    cms_langs = settings.CMS_LANGUAGES
    dels_lang = next(lang for lang in cms_langs.get(1, []) if lang["code"] == "de-ls")
    original = dels_lang["public"]

    settings.EASYLANG_ENABLED = value
    dels_lang["public"] = value
    cms_langs.pop(VERIFIED, None)

    yield value

    dels_lang["public"] = original
    cms_langs.pop(VERIFIED, None)


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


def maybe_login(client, request, user_fixture):
    """Log in as the given user fixture, if provided."""
    if user_fixture:
        user = request.getfixturevalue(user_fixture)
        client.force_login(user)


@pytest.fixture
def admin_user(db):
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin", email="admin@example.com", password="admin"
    )


@pytest.fixture
def staff_user(db):
    User = get_user_model()
    user = User.objects.create_user(
        username="staff", email="staff@example.com", password="staff"
    )
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


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

    After creating the page we re-populate the global APP_RESOLVERS so
    that applications_page_check() can find the apphook page (it is
    normally populated at cms.urls import time, before any test data exists).
    """
    page = cms_page(
        "Blog", "de", slug="blog", apphook="FdsBlogApp", apphook_namespace="blog"
    )
    add_language_to_page(page, "de-ls", "Blog", admin_user, slug="blog")

    # Refresh resolvers after adding the de-ls translation.
    clear_app_resolvers()
    get_app_patterns()

    return page


@pytest.fixture
def event_page(cms_page):
    """CMS apphook page for events, published in de only (no de-ls)."""
    return cms_page(
        "Veranstaltungen",
        "de",
        slug="veranstaltungen",
        apphook="FdsEventsApp",
        apphook_namespace="fds_events",
    )


def create_article(
    language,
    category,
    title="Test Article",
    publish=True,
    **kwargs,
):
    """Create a published blog article linked to the current site."""
    defaults = {
        "title": title,
        "slug": title.lower().replace(" ", "-"),
        "language": language,
        "start_publication": timezone.now() - timedelta(hours=1),
    }

    if publish:
        defaults["status"] = PUBLISHED

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


def create_event(title="Test Event", slug=None, **kwargs):
    """Create a public event."""
    defaults = {
        "title": title,
        "slug": slug or title.lower().replace(" ", "-"),
        "description": "A test event",
        "start_date": timezone.now() + timedelta(hours=1),
        "end_date": timezone.now() + timedelta(hours=2),
        "public": True,
    }
    defaults.update(kwargs)
    return Event.objects.create(**defaults)


@pytest.mark.django_db
class TestEasyLanguageRedirect:
    """Tests what happens when navigating to /de-ls/... directly.

    Non-CMS pages should be redirected to the default language equivalent.
    CMS pages with a de-ls translation should render; without one they redirect.
    Admin URLs are exempt from redirection.
    Blog views additionally gate de-ls access on EASYLANG_ENABLED / staff status.
    """

    # --- Non-CMS ---

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_non_cms_redirects(self, client, easylang_enabled):
        response = get(client, "/de-ls/account/login/")
        assert response.status_code == 301
        assert response["Location"] == "/account/login/"

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_non_cms_preserves_query_string(self, client, easylang_enabled):
        response = get(client, "/de-ls/account/login/", QUERY_STRING="next=/")
        assert response.status_code == 301
        assert response["Location"] == "/account/login/?next=/"

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_non_cms_post_not_redirected(self, client, easylang_enabled):
        """POST requests to /de-ls/ are not redirected (middleware only handles GET)."""
        response = client.post("/de-ls/account/login/", HTTP_HOST=HTTP_HOST)
        assert response.status_code != 301

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_non_cms_de_not_redirected(self, client, easylang_enabled):
        response = get(client, "/account/login/")
        assert response.status_code != 301

    # --- Admin (exception) ---

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_admin_not_redirected(self, client, admin_user, easylang_enabled):
        client.force_login(admin_user)
        response = get(client, "/de-ls/admin/")
        assert response.status_code == 200

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_admin_subpage_not_redirected(self, client, admin_user, easylang_enabled):
        client.force_login(admin_user)
        response = get(client, "/de-ls/admin/fds_blog/article/")
        assert response.status_code == 200

    # --- Plain CMS page ---

    @pytest.mark.parametrize(
        "easylang_enabled, user_fixture, expected_status",
        EASYLANG_GATE_PARAMS,
        ids=EASYLANG_GATE_IDS,
        indirect=["easylang_enabled"],
    )
    def test_cms_page_with_translation(
        self,
        client,
        admin_user,
        cms_page,
        request,
        easylang_enabled,
        user_fixture,
        expected_status,
    ):
        maybe_login(client, request, user_fixture)
        page = cms_page("Testseite", "de")
        add_language_to_page(page, "de-ls", "Testseite Leicht", admin_user)

        de_ls_url = page.get_absolute_url("de-ls")
        response = get(client, de_ls_url)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "easylang_enabled, user_fixture, expected_status",
        EASYLANG_GATE_PARAMS,
        ids=EASYLANG_GATE_IDS,
        indirect=["easylang_enabled"],
    )
    def test_cms_page_with_unpublished_translation(
        self,
        client,
        admin_user,
        cms_page,
        request,
        easylang_enabled,
        user_fixture,
        expected_status,
    ):
        """An unpublished de-ls translation should behave like no translation."""
        maybe_login(client, request, user_fixture)
        page = cms_page("Testseite", "de")
        add_language_to_page(
            page, "de-ls", "Testseite Leicht", admin_user, publish=False
        )

        de_url = page.get_absolute_url("de")
        de_ls_url = f"/de-ls{de_url}"
        response = get(client, de_ls_url)
        # Allowed through the gate → 302 redirect to de (no published translation).
        assert response.status_code == (302 if expected_status == 200 else 404)
        if response.status_code == 302:
            assert de_url in response["Location"]

    @pytest.mark.parametrize(
        "easylang_enabled, user_fixture, expected_status",
        EASYLANG_GATE_PARAMS,
        ids=EASYLANG_GATE_IDS,
        indirect=["easylang_enabled"],
    )
    def test_cms_page_without_translation(
        self,
        client,
        cms_page,
        request,
        easylang_enabled,
        user_fixture,
        expected_status,
    ):
        maybe_login(client, request, user_fixture)
        page = cms_page("Testseite", "de")

        de_url = page.get_absolute_url("de")
        de_ls_url = f"/de-ls{de_url}"
        response = get(client, de_ls_url)

        # Allowed through the gate → 302 redirect to de (no translation).
        assert response.status_code == (302 if expected_status == 200 else 404)
        if response.status_code == 302:
            assert de_url in response["Location"]

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_cms_page_de_not_redirected(self, client, cms_page, easylang_enabled):
        page = cms_page("Testseite", "de")

        de_url = page.get_absolute_url("de")
        response = get(client, de_url)
        assert response.status_code == 200

    # --- CMS apphook page ---

    @pytest.mark.parametrize(
        "easylang_enabled, user_fixture, expected_status",
        EASYLANG_GATE_PARAMS,
        ids=EASYLANG_GATE_IDS,
        indirect=["easylang_enabled"],
    )
    def test_apphook_with_translation(
        self,
        client,
        blog_page,
        request,
        easylang_enabled,
        user_fixture,
        expected_status,
    ):
        maybe_login(client, request, user_fixture)

        de_ls_url = blog_page.get_absolute_url("de-ls")
        response = get(client, de_ls_url)
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "easylang_enabled, user_fixture, expected_status",
        EASYLANG_GATE_PARAMS,
        ids=EASYLANG_GATE_IDS,
        indirect=["easylang_enabled"],
    )
    def test_apphook_without_translation(
        self,
        client,
        event_page,
        request,
        easylang_enabled,
        user_fixture,
        expected_status,
    ):
        maybe_login(client, request, user_fixture)
        de_url = event_page.get_absolute_url("de")
        de_ls_url = f"/de-ls{de_url}"
        response = get(client, de_ls_url)
        # Allowed through the gate → 302 redirect to de (no de-ls translation).
        assert response.status_code == (302 if expected_status == 200 else 404)
        if response.status_code == 302:
            assert de_url in response["Location"]

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_apphook_de_not_redirected(self, client, blog_page, easylang_enabled):
        de_url = blog_page.get_absolute_url("de")
        response = get(client, de_url)
        assert response.status_code == 200

    # --- Blog article ---

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_blog_de_article_accessible(self, client, category_de, easylang_enabled):
        article = create_article("de", category_de)
        response = get(client, article.get_absolute_url())
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "easylang_enabled, user_fixture, expected_status",
        EASYLANG_GATE_PARAMS,
        ids=EASYLANG_GATE_IDS,
        indirect=["easylang_enabled"],
    )
    def test_blog_de_ls_article_accessible(
        self,
        client,
        blog_page,
        category_de_ls,
        request,
        easylang_enabled,
        user_fixture,
        expected_status,
    ):
        maybe_login(client, request, user_fixture)

        article = create_article("de-ls", category_de_ls)
        response = get(client, article.get_absolute_url())
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "easylang_enabled, user_fixture",
        [
            (True, None),
            (False, None),
            (False, "staff_user"),
        ],
        ids=["enabled-anonymous", "disabled-anonymous", "disabled-staff"],
        indirect=["easylang_enabled"],
    )
    def test_blog_de_article_not_found_via_de_ls(
        self,
        client,
        blog_page,
        category_de_ls,
        request,
        easylang_enabled,
        user_fixture,
    ):
        """A translated article is not accessible under /de-ls/ (different slug → 404)."""
        maybe_login(client, request, user_fixture)

        shared_uuid = uuid.uuid4()
        de_article = create_article(
            "de", category_de_ls, title="German", uuid=shared_uuid
        )
        create_article("de-ls", category_de_ls, title="Easy", uuid=shared_uuid)

        de_url = de_article.get_absolute_url()
        de_ls_url = f"/de-ls{de_url}"
        response = get(client, de_ls_url)
        assert response.status_code == 404

    # --- Event (apphook subpage) ---

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_event_de_accessible(self, client, event_page, easylang_enabled):
        event = create_event()
        response = get(client, event.get_absolute_url())
        assert response.status_code == 200

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_event_de_ls_redirects_without_apphook_translation(
        self, client, event_page, easylang_enabled
    ):
        """An event under /de-ls/ should redirect when the apphook page has no de-ls."""
        event = create_event()
        de_url = event.get_absolute_url()
        de_ls_url = f"/de-ls{de_url}"
        response = get(client, de_ls_url)
        assert response.status_code == 301
        assert de_url in response["Location"]

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_event_de_ls_redirects_with_apphook_translation(
        self, client, event_page, admin_user, easylang_enabled
    ):
        """An event under /de-ls/ should redirect even when the apphook page has de-ls,
        because individual events have no translated content."""
        add_language_to_page(event_page, "de-ls", "Veranstaltungen", admin_user)
        clear_app_resolvers()
        get_app_patterns()

        event = create_event()
        de_url = event.get_absolute_url()
        de_ls_url = f"/de-ls{de_url}"
        response = get(client, de_ls_url)
        assert response.status_code == 301
        assert de_url in response["Location"]


@pytest.mark.django_db
class TestEasylangToggle:
    """Tests `easylang_toggle` template tag output.

    target_url points to the specific translated page when actual translated
    content exists — plain CMS pages with a published translation, apphook
    root pages with a published translation, and blog articles linked by UUID.
    All other cases (non-CMS pages, apphook subpages, unlinked articles) fall
    back to the target language home page.
    """

    def _get_toggle_context(self, client, url):
        """Make a real GET request, then call the tag function with request context."""
        from django.template import Context

        from fragdenstaat_de.fds_easylang.templatetags.easylang_tags import (
            easylang_toggle,
        )

        response = get(client, url)
        assert response.status_code == 200

        request = response.wsgi_request
        view = (
            getattr(response, "context_data", {}).get("view")
            if hasattr(response, "context_data")
            else None
        )
        context = Context({"request": request, "view": view})
        return easylang_toggle(context)

    # --- Non-CMS page ---

    def test_non_cms_no_translation_from_de(self, client):
        ctx = self._get_toggle_context(client, "/account/login/")
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == "/de-ls/"

    def test_non_cms_no_translation_from_de_ls(self, client):
        """de-ls non-CMS URLs redirect, so we check the redirected response."""
        response = get(client, "/de-ls/account/login/")
        assert response.status_code == 301
        ctx = self._get_toggle_context(client, response["Location"])
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == "/de-ls/"

    # --- Plain CMS page ---

    def test_cms_page_with_translation_from_de(self, client, admin_user, cms_page):
        page = cms_page("Testseite", "de")
        add_language_to_page(page, "de-ls", "Testseite Leicht", admin_user)

        ctx = self._get_toggle_context(client, page.get_absolute_url("de"))
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == page.get_absolute_url("de-ls")

    @pytest.mark.parametrize("easylang_enabled", [True], indirect=True)
    def test_cms_page_with_translation_from_de_ls(
        self, client, admin_user, cms_page, easylang_enabled
    ):
        page = cms_page("Testseite", "de")
        add_language_to_page(page, "de-ls", "Testseite Leicht", admin_user)

        ctx = self._get_toggle_context(client, page.get_absolute_url("de-ls"))
        assert ctx["current_language"] == "de-ls"
        assert ctx["target_language"] == "de"
        assert ctx["target_url"] == page.get_absolute_url("de")

    def test_cms_page_with_unpublished_translation(self, client, admin_user, cms_page):
        """An unpublished de-ls translation should not count as available."""
        page = cms_page("Testseite", "de")
        add_language_to_page(
            page, "de-ls", "Testseite Leicht", admin_user, publish=False
        )

        ctx = self._get_toggle_context(client, page.get_absolute_url("de"))
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == "/de-ls/"

    def test_cms_page_without_translation(self, client, cms_page):
        page = cms_page("Testseite", "de")

        ctx = self._get_toggle_context(client, page.get_absolute_url("de"))
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == "/de-ls/"

    # --- CMS apphook page ---

    def test_apphook_with_translation_from_de(self, client, blog_page):
        ctx = self._get_toggle_context(client, blog_page.get_absolute_url("de"))
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == blog_page.get_absolute_url("de-ls")

    @pytest.mark.parametrize("easylang_enabled", [True], indirect=True)
    def test_apphook_with_translation_from_de_ls(
        self, client, blog_page, easylang_enabled
    ):
        ctx = self._get_toggle_context(client, blog_page.get_absolute_url("de-ls"))
        assert ctx["current_language"] == "de-ls"
        assert ctx["target_language"] == "de"
        assert ctx["target_url"] == blog_page.get_absolute_url("de")

    def test_apphook_without_translation(self, client, event_page):
        """CMS apphook page without de-ls: target_url falls back to language home."""
        ctx = self._get_toggle_context(client, event_page.get_absolute_url("de"))
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == "/de-ls/"

    # --- Blog article ---

    def test_blog_with_translation_from_de(self, client, blog_page, category_de_ls):
        """Two articles linked by uuid — toggle should detect the translation."""
        shared_uuid = uuid.uuid4()
        de_article = create_article(
            "de", category_de_ls, title="German", uuid=shared_uuid
        )
        de_ls_article = create_article(
            "de-ls", category_de_ls, title="Easy", uuid=shared_uuid
        )

        ctx = self._get_toggle_context(client, de_article.get_absolute_url())
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == de_ls_article.get_absolute_url()

    @pytest.mark.parametrize(
        "easylang_enabled, user_fixture",
        [
            (True, None),
            (False, "staff_user"),
        ],
        ids=[
            "enabled-anonymous",
            "disabled-staff",
        ],
        indirect=["easylang_enabled"],
    )
    def test_blog_with_translation_from_de_ls(
        self,
        client,
        blog_page,
        category_de_ls,
        request,
        easylang_enabled,
        user_fixture,
    ):
        """Toggle from de-ls article should point back to de."""
        maybe_login(client, request, user_fixture)

        shared_uuid = uuid.uuid4()
        de_article = create_article(
            "de", category_de_ls, title="German", uuid=shared_uuid
        )
        de_ls_article = create_article(
            "de-ls", category_de_ls, title="Easy", uuid=shared_uuid
        )

        ctx = self._get_toggle_context(client, de_ls_article.get_absolute_url())
        assert ctx["current_language"] == "de-ls"
        assert ctx["target_language"] == "de"
        assert ctx["target_url"] == de_article.get_absolute_url()

    def test_blog_with_unpublished_translation(
        self,
        client,
        blog_page,
        category_de_ls,
    ):
        """An unpublished de-ls translation should not count as available."""
        shared_uuid = uuid.uuid4()
        de_article = create_article(
            "de", category_de_ls, title="German", uuid=shared_uuid
        )
        create_article(
            "de-ls", category_de_ls, title="Easy", uuid=shared_uuid, publish=False
        )

        ctx = self._get_toggle_context(client, de_article.get_absolute_url())
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == "/de-ls/"

    def test_blog_without_translation(self, client, blog_page, category_de):
        """Single de article with no de-ls counterpart: target_url falls back to language home."""
        article = create_article("de", category_de)

        ctx = self._get_toggle_context(client, article.get_absolute_url())
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == "/de-ls/"

    @pytest.mark.parametrize(
        "easylang_enabled, user_fixture",
        [
            (True, None),
            (False, "staff_user"),
        ],
        ids=[
            "enabled-anonymous",
            "disabled-staff",
        ],
        indirect=["easylang_enabled"],
    )
    def test_blog_de_ls_without_de_counterpart(
        self,
        client,
        blog_page,
        category_de_ls,
        request,
        easylang_enabled,
        user_fixture,
    ):
        """Standalone de-ls article with no linked de article: target_url falls back to language home."""
        maybe_login(client, request, user_fixture)

        article = create_article("de-ls", category_de_ls)

        ctx = self._get_toggle_context(client, article.get_absolute_url())
        assert ctx["current_language"] == "de-ls"
        assert ctx["target_language"] == "de"
        assert ctx["target_url"] == "/de/"

    # --- Event (apphook subpage) ---

    def test_event_without_apphook_translation(self, client, event_page):
        """Event detail page — apphook has no de-ls: target_url falls back to language home."""
        event = create_event()
        ctx = self._get_toggle_context(client, event.get_absolute_url())
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == "/de-ls/"

    def test_event_with_apphook_translation(self, client, event_page, admin_user):
        """Event detail page — even with a de-ls apphook, individual events have no translated content, so the toggle should not offer a link."""
        add_language_to_page(event_page, "de-ls", "Veranstaltungen", admin_user)
        clear_app_resolvers()
        get_app_patterns()

        event = create_event()
        ctx = self._get_toggle_context(client, event.get_absolute_url())
        assert ctx["current_language"] == "de"
        assert ctx["target_language"] == "de-ls"
        assert ctx["target_url"] == "/de-ls/"


@pytest.mark.django_db
class TestEasylangContextProcessor:
    """Tests that the context processor exposes easylang_enabled."""

    @pytest.mark.parametrize("easylang_enabled", [True, False], indirect=True)
    def test_easylang_enabled_in_context(self, client, easylang_enabled):
        response = get(client, "/account/login/")
        assert response.context["EASYLANG_ENABLED"] is easylang_enabled


class FakeBlogView(BaseBlogView):
    base_template_name = "article_list.html"


class TestBaseBlogViewTemplateNames:
    def test_de_ls_returns_prefixed_and_fallback(self):
        translation.activate("de-ls")
        view = FakeBlogView()
        names = view.get_template_names()
        assert names == [
            "de-ls/fds_blog/article_list.html",
            "fds_blog/article_list.html",
        ]

    def test_de_returns_prefixed_and_fallback(self):
        translation.activate("de")
        view = FakeBlogView()
        names = view.get_template_names()
        assert names == [
            "de/fds_blog/article_list.html",
            "fds_blog/article_list.html",
        ]

    def test_language_switch(self):
        view = FakeBlogView()

        translation.activate("de")
        de_names = view.get_template_names()

        translation.activate("de-ls")
        de_ls_names = view.get_template_names()

        assert de_names != de_ls_names
        assert "de/fds_blog/article_list.html" in de_names
        assert "de-ls/fds_blog/article_list.html" in de_ls_names


class TestArticleDetailViewTemplateNames:
    def _make_view(self, detail_template="fds_blog/article_detail.html"):
        view = ArticleDetailView()

        class FakeArticle:
            pass

        obj = FakeArticle()
        obj.detail_template = detail_template
        view.object = obj
        return view

    def test_de_ls_returns_prefixed_and_fallback(self):
        translation.activate("de-ls")
        view = self._make_view()
        names = view.get_template_names()
        assert names == [
            "de-ls/fds_blog/article_detail.html",
            "fds_blog/article_detail.html",
        ]

    def test_de_returns_prefixed_and_fallback(self):
        translation.activate("de")
        view = self._make_view()
        names = view.get_template_names()
        assert names == [
            "de/fds_blog/article_detail.html",
            "fds_blog/article_detail.html",
        ]
