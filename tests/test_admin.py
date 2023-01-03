from django.conf import settings
from django.urls import URLResolver, reverse

import pytest


@pytest.mark.django_db
def test_admin_apps_for_login(client, dummy_user):
    """Test that any installed admin apps do not provide login functionality."""

    def get_login_path(resolver):
        for pattern in resolver.url_patterns:
            if pattern.name == "login":
                yield reverse(
                    "%s:%s" % (resolver.namespace, pattern.name),
                    current_app=resolver.app_name,
                )
                break

    def get_admins(pattern_list):
        for item in pattern_list:
            if not isinstance(item, URLResolver):
                continue
            if item.app_name == "admin":
                yield item
            else:
                yield from get_admins(item.url_patterns)

    patterns = __import__(settings.ROOT_URLCONF, {}, {}, [""]).urlpatterns

    dummy_user.is_staff = True
    dummy_user.save()
    login_url = reverse("account-login")

    admin_resolvers = get_admins(patterns)
    admin_login_paths = [
        cb for resolver in admin_resolvers for cb in get_login_path(resolver)
    ]
    for login_path in admin_login_paths:
        response = client.get(login_path)
        assert response.status_code == 302
        assert response["Location"].startswith(login_url)

        response = client.post(
            login_path, {"username": dummy_user.email, "password": "froide"}
        )
        assert client.session.get("_auth_user_id") is None
        assert response.status_code == 302
        assert response["Location"].startswith(login_url)
