"""
Contains patched CSRF view middleware for Django and Django Rest Framework
that ignores the referrer check when using https.
"""

from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.utils.http import is_same_domain
from django.middleware.csrf import (
    CsrfViewMiddleware,
    _sanitize_token,
    _compare_masked_tokens,
    REASON_BAD_REFERER,
    REASON_NO_CSRF_COOKIE,
    REASON_BAD_TOKEN,
    REASON_MALFORMED_REFERER,
    REASON_INSECURE_REFERER,
)

from rest_framework import authentication


class CsrfViewIlfMiddleware(CsrfViewMiddleware):
    """
    Allow empty referer on secure websites
    One of our power user disables referers and still wants to use the site.
    """

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if getattr(request, "csrf_processing_done", False):
            return None

        # Wait until request.META["CSRF_COOKIE"] has been manipulated before
        # bailing out, so that get_token still works
        if getattr(callback, "csrf_exempt", False):
            return None

        # Assume that anything not defined as 'safe' by RFC7231 needs protection
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            if getattr(request, "_dont_enforce_csrf_checks", False):
                # Mechanism to turn off CSRF checks for test suite.
                # It comes after the creation of CSRF cookies, so that
                # everything else continues to work exactly the same
                # (e.g. cookies are sent, etc.), but before any
                # branches that call reject().
                return self._accept(request)

            if request.is_secure():
                # Suppose user visits http://example.com/
                # An active network attacker (man-in-the-middle, MITM) sends a
                # POST form that targets https://example.com/detonate-bomb/ and
                # submits it via JavaScript.
                #
                # The attacker will need to provide a CSRF cookie and token, but
                # that's no problem for a MITM and the session-independent
                # secret we're using. So the MITM can circumvent the CSRF
                # protection. This is true for any HTTP connection, but anyone
                # using HTTPS expects better! For this reason, for
                # https://example.com/ we need additional protection that treats
                # http://example.com/ as completely untrusted. Under HTTPS,
                # Barth et al. found that the Referer header is missing for
                # same-domain requests in only about 0.2% of cases or less, so
                # we can use strict Referer checking.
                referer = request.META.get("HTTP_REFERER")

                # -- Change from original here -- #
                # Only checks referer if it is present.
                # It's not a failure condition if the referer is not present.
                # Our site is HTTPS-only which does not need to rely on
                # referer checking. Above example does not apply.
                if referer is not None:
                    referer = urlparse(referer)

                    # Make sure we have a valid URL for Referer.
                    if "" in (referer.scheme, referer.netloc):
                        return self._reject(request, REASON_MALFORMED_REFERER)

                    # Ensure that our Referer is also secure.
                    if referer.scheme != "https" and not referer.netloc.endswith(
                        ".onion"
                    ):
                        return self._reject(request, REASON_INSECURE_REFERER)

                    # If there isn't a CSRF_COOKIE_DOMAIN, require an exact match
                    # match on host:port. If not, obey the cookie rules (or those
                    # for the session cookie, if CSRF_USE_SESSIONS).
                    good_referer = (
                        settings.SESSION_COOKIE_DOMAIN
                        if settings.CSRF_USE_SESSIONS
                        else settings.CSRF_COOKIE_DOMAIN
                    )
                    if good_referer is not None:
                        server_port = request.get_port()
                        if server_port not in ("443", "80"):
                            good_referer = "%s:%s" % (good_referer, server_port)
                    else:
                        try:
                            # request.get_host() includes the port.
                            good_referer = request.get_host()
                        except DisallowedHost:
                            pass

                    # Create a list of all acceptable HTTP referers, including the
                    # current host if it's permitted by ALLOWED_HOSTS.
                    good_hosts = list(settings.CSRF_TRUSTED_ORIGINS)
                    if good_referer is not None:
                        good_hosts.append(good_referer)

                    if not any(
                        is_same_domain(referer.netloc, host) for host in good_hosts
                    ):
                        reason = REASON_BAD_REFERER % referer.geturl()
                        return self._reject(request, reason)

            csrf_token = self._get_token(request)
            if csrf_token is None:
                # No CSRF cookie. For POST requests, we insist on a CSRF cookie,
                # and in this way we can avoid all CSRF attacks, including login
                # CSRF.
                return self._reject(request, REASON_NO_CSRF_COOKIE)

            # Check non-cookie token for match.
            request_csrf_token = ""
            if request.method == "POST":
                try:
                    request_csrf_token = request.POST.get("csrfmiddlewaretoken", "")
                except OSError:
                    # Handle a broken connection before we've completed reading
                    # the POST data. process_view shouldn't raise any
                    # exceptions, so we'll ignore and serve the user a 403
                    # (assuming they're still listening, which they probably
                    # aren't because of the error).
                    pass

            if request_csrf_token == "":
                # Fall back to X-CSRFToken, to make things easier for AJAX,
                # and possible for PUT/DELETE.
                request_csrf_token = request.META.get(settings.CSRF_HEADER_NAME, "")

            request_csrf_token = _sanitize_token(request_csrf_token)
            if not _compare_masked_tokens(request_csrf_token, csrf_token):
                return self._reject(request, REASON_BAD_TOKEN)

        return self._accept(request)


class CsrfViewIlfDrfMiddleware(CsrfViewIlfMiddleware):
    # Same as in rest_framework.authentication.CSRFCheck
    def _reject(self, request, reason):
        # Return the failure reason instead of an HttpResponse
        return reason


# Monkey patch DRF CSRF check to use our own middleware
authentication.CSRFCheck = CsrfViewIlfDrfMiddleware
