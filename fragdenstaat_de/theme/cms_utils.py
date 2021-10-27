from django.conf import settings
from cms.middleware.language import LanguageCookieMiddleware


class HostLanguageCookieMiddleware(LanguageCookieMiddleware):
    def process_response(self, request, response):
        """Don't set django_language cookie on non-primary domain"""
        if request.META.get("HTTP_HOST") != settings.ALLOWED_HOSTS[0]:
            return response
        return super().process_response(request, response)
