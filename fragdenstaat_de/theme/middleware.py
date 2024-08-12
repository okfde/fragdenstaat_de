from django.middleware.clickjacking import XFrameOptionsMiddleware


class XFrameOptionsCSPMiddleware(XFrameOptionsMiddleware):
    def process_response(self, request, response):
        response = super().process_response(request, response)
        current_page = getattr(request, "current_page", None)
        if current_page is not None:
            # current_page is a lazy object that only evaluates to None on attr access
            extension = getattr(current_page, "fdspageextension", None)
            if extension is not None and extension.frame_ancestors:
                frame_ancestor_urls = " ".join(extension.get_frame_ancestors())
                response.headers["Content-Security-Policy"] = (
                    "frame-ancestors 'self' %s" % frame_ancestor_urls
                )
                del response["X-Frame-Options"]
        if response.has_header("X-Frame-Options"):
            response.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
        return response
