from django.conf import settings

from cms.middleware.language import LanguageCookieMiddleware


class HostLanguageCookieMiddleware(LanguageCookieMiddleware):
    def __call__(self, request):
        """Don't set django_language cookie on non-primary domain"""
        if request.META.get("HTTP_HOST") != settings.ALLOWED_HOSTS[0]:
            return self.get_response(request)
        return super().__call__(request)
