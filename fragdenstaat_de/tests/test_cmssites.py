from contextlib import contextmanager

from django.contrib.sites.models import Site

import pytest
from cms import api as cms_api
from configurations.utils import uppercase_attributes
from configurations.values import Value, setup_value

from fragdenstaat_de.fds_cms.models import SiteSettings
from fragdenstaat_de.settings.cms import CMSSiteBase
from fragdenstaat_de.tests.utils import publish_page_content


@contextmanager
def apply_configuration(configuration_class, settings, ignore=None, overrides=None):
    if ignore is None:
        ignore = []
    if overrides is None:
        overrides = {}
    configuration_class.pre_setup()
    configuration_class.setup()
    obj = configuration_class()
    attributes = uppercase_attributes(obj).items()

    new_config = []

    for name, value in attributes:
        if name in overrides:
            value = overrides[name]
        elif name in ignore:
            continue
        elif callable(value) and not getattr(value, "pristine", False):
            value = value()
            # in case a method returns a Value instance we have
            # to do the same as the Configuration.setup method
            if isinstance(value, Value):
                setup_value(settings, name, value)
                continue
        if not hasattr(settings, name):
            new_config.append(name)
        setattr(settings, name, value)

    yield

    for name in new_config:
        delattr(settings, name)


@contextmanager
def setup_site(
    settings,
    domain,
    base_template,
    user,
):
    site = Site.objects.create(id=2, domain=domain)
    SiteSettings.objects.create(
        site=site,
        settings={
            "SITE_NAME": "Some CMS Site",
            "SITE_EMAIL": "cms@example.org",
            "SITE_URL": f"http://{domain}",
            "SITE_LOGO": "",
            "SENTRY_JS_URL": "",
            "MATOMO_SITE_ID": "42",
            "CMSSITE_BASE_TEMPLATE": base_template,
        },
    )
    page = cms_api.create_page(
        "Test Index",
        "cms/page.html",
        "de",
        slug="",
        overwrite_url="/",
        created_by=user,
        site=site,
    )
    page.set_as_homepage()

    publish_page_content(page, "de", user)

    with apply_configuration(
        CMSSiteBase,
        settings,
        ignore=["DATABASES"],
        overrides={"ALLOWED_HOSTS": [domain]},
    ):
        yield site


@pytest.fixture
def cms_site(settings, dummy_user):
    domain = "cms.local"
    with setup_site(settings, domain, "fds_base.html", dummy_user) as site:
        yield site


@pytest.mark.django_db
def test_cms_site_bad_host_header(client, cms_site):
    response = client.get("/")
    assert response.status_code == 400


@pytest.mark.django_db
def test_cms_site_pages(client, cms_site, settings):
    headers = {"Host": cms_site.domain, "Origin": f"http://{cms_site.domain}/"}
    response = client.get("/", headers=headers, HTTP_HOST=cms_site.domain)
    assert response.status_code == 200
    assert "/static/main.js" in response.content.decode()
    assert (
        f"matomo.php?idsite={cms_site.site_settings.settings['MATOMO_SITE_ID']}"
        in response.content.decode()
    )
    response = client.get("/cookies/", headers=headers)
    assert response.status_code == 200

    response = client.get("/does-not-exist/", headers=headers)
    assert response.status_code == 404


@pytest.mark.django_db
def test_cms_grs(client, settings, dummy_user):
    with setup_site(
        settings, "gegenrechtsschutz.de", "grs_base.html", dummy_user
    ) as cms_site:
        headers = {"Host": cms_site.domain, "Origin": f"http://{cms_site.domain}/"}
        response = client.get("/", headers=headers, HTTP_HOST=cms_site.domain)
        assert response.status_code == 200
        assert "/static/gegenrechtsschutz.js" in response.content.decode()
        assert (
            f"matomo.php?idsite={cms_site.site_settings.settings['MATOMO_SITE_ID']}"
            in response.content.decode()
        )
        response = client.get("/cookies/", headers=headers)
        assert response.status_code == 200

        response = client.get("/does-not-exist/", headers=headers)
        assert response.status_code == 404


@pytest.mark.django_db
def test_cms_ubf(client, settings, dummy_user):
    with setup_site(
        settings, "ueberbrueckungsfonds.de", "ubf_base.html", dummy_user
    ) as cms_site:
        headers = {"Host": cms_site.domain, "Origin": f"http://{cms_site.domain}/"}
        response = client.get("/", headers=headers, HTTP_HOST=cms_site.domain)
        assert response.status_code == 200
        assert "/static/ubf.js" in response.content.decode()
        assert (
            f"matomo.php?idsite={cms_site.site_settings.settings['MATOMO_SITE_ID']}"
            in response.content.decode()
        )
        response = client.get("/cookies/", headers=headers)
        assert response.status_code == 200

        response = client.get("/does-not-exist/", headers=headers)
        assert response.status_code == 404
