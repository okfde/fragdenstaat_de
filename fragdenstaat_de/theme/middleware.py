from django.middleware.clickjacking import XFrameOptionsMiddleware


class XFrameOptionsCSPMiddleware(XFrameOptionsMiddleware):
    def process_response(self, request, response):
        response = super().process_response(request, response)
        if response.has_header("X-Frame-Options"):
            response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
        return response
