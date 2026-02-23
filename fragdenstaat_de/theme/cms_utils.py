from django.conf import settings
from django.shortcuts import redirect

from cms.middleware.language import LanguageCookieMiddleware


class LanguageUtilsMiddleware(LanguageCookieMiddleware):
    def __call__(self, request):
        """
        Don't set django_language cookie on non-primary domain
        Also redirect non-CMS pages to default language if the request is for a sub-language.
        Needs to be placed after:
          - django.middleware.locale.LocaleMiddleware
          - cms.middleware.page.CurrentPageMiddleware
        """
        if (
            not settings.DEBUG
            and request.META.get("HTTP_HOST") != settings.ALLOWED_HOSTS[0]
        ):
            return self.get_response(request)
        if (
            request.method == "GET"
            and request.LANGUAGE_CODE != settings.LANGUAGE_CODE
            and request.LANGUAGE_CODE.startswith(settings.LANGUAGE_CODE)
            and not request.current_page
            # Ignore admin to avoid problems when editing sublanguage CMS pages.
            and not request.path.startswith(f"/{request.LANGUAGE_CODE}/admin/")
        ):
            path = request.get_full_path().removeprefix(f"/{request.LANGUAGE_CODE}")
            return redirect(path, permanent=True)

        return super().__call__(request)
