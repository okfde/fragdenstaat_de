import pytest

from fragdenstaat_de.settings.cms import CMSSiteBase, GegenrechtsschutzMixin, UbfMixin

CMSSITES = [
    (GegenrechtsschutzMixin, "gegenrechtsschutz.js"),
    (UbfMixin, "ubf.js"),
]


@pytest.fixture
def cmssite_settings(settings, request):
    engine, *other_engines = settings.TEMPLATES
    settings.TEMPLATES = [
        {**engine, "DIRS": CMSSiteBase.TEMPLATES[0]["DIRS"]},
        *other_engines,
    ]
    settings.CMSSITE_BASE_TEMPLATE = request.param.CMSSITE_BASE_TEMPLATE
    return settings


@pytest.mark.django_db
@pytest.mark.parametrize(
    "cmssite_settings,entry_point",
    CMSSITES,
    indirect=["cmssite_settings"],
)
def test_cookies_page_loads_frontend_assets(client, cmssite_settings, entry_point):
    response = client.get("/cookies/")
    assert response.status_code == 200
    assert entry_point in response.content.decode()
