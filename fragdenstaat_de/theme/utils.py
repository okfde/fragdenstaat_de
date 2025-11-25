import logging


class Ignore501Errors(logging.Filter):
    def filter(self, record):
        status_code = getattr(record, "status_code", None)

        if status_code:
            if status_code == 501:
                return False
        return True


def handler500(request):
    """
    500 error handler which includes ``request`` in the context.
    """

    from django.shortcuts import render

    return render(request, "500.html", {"request": request}, status=500)
