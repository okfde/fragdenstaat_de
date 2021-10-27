import logging


class Ignore501Errors(logging.Filter):
    def filter(self, record):
        status_code = getattr(record, "status_code", None)

        if status_code:
            if status_code == 501:
                return False
        return True
