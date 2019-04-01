from django.conf import settings
from django.contrib.redirects.models import Redirect
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.redirects.middleware import RedirectFallbackMiddleware

from froide.helper.utils import update_query_params


class PathRedirectFallbackMiddleware(RedirectFallbackMiddleware):
    '''
    A custom version of Djangos RedirectFallbackMiddleware
    that looks at request.path instead of request.get_full_path(),
    so it ignores any query strings and just looks at path.
    It then merges querystrings of request and new path.
    '''
    def process_response(self, request, response):
        # No need to check for a redirect for non-404 responses.
        if response.status_code != 404:
            return response

        path = request.path
        current_site = get_current_site(request)

        r = None
        try:
            r = Redirect.objects.get(site=current_site, old_path=path)
        except Redirect.DoesNotExist:
            pass
        if r is None and settings.APPEND_SLASH and not request.path.endswith('/'):
            try:
                r = Redirect.objects.get(
                    site=current_site,
                    old_path=request.path + '/',
                )
            except Redirect.DoesNotExist:
                pass
        if r is not None:
            if r.new_path == '':
                return self.response_gone_class()
            full_path = update_query_params(r.new_path, request.GET)
            return self.response_redirect_class(full_path)

        # No redirect was found. Return the response.
        return response
