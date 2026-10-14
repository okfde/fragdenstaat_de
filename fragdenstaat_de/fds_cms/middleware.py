from django.contrib.sites.models import Site
from django.http.request import split_domain_port
from django.utils.deprecation import MiddlewareMixin

SITE_CACHE = {}


def get_site_by_request(request):
    """
    Modified from django.contrib.sites SiteManager
    """
    qs = Site.objects.select_related("site_settings")
    host = request.get_host()
    try:
        # First attempt to look up the site by host with or without port.
        if host not in SITE_CACHE:
            SITE_CACHE[host] = qs.get(domain__iexact=host)
        return SITE_CACHE[host]
    except Site.DoesNotExist:
        # Fallback to looking up site after stripping port from the host.
        domain, port = split_domain_port(host)
        if domain not in SITE_CACHE:
            SITE_CACHE[domain] = qs.get(domain__iexact=domain)
        return SITE_CACHE[domain]


class CMSSiteMiddleware(MiddlewareMixin):
    """
    Middleware that sets `site` attribute to request object.
    """

    async_capable = False

    def process_request(self, request):
        request.site = get_site_by_request(request)
