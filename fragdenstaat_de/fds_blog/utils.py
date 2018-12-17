from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.test.client import RequestFactory


def get_request(language=None, path='/'):
    request_factory = RequestFactory()
    request = request_factory.get(path)
    request.session = {}
    request.LANGUAGE_CODE = language or settings.LANGUAGE_CODE

    # Needed for plugin rendering.
    request.current_page = None
    request.user = AnonymousUser()
    return request
