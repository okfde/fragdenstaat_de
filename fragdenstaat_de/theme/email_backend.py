from django.conf import settings

from djcelery_email.backends import CeleryEmailBackend
from djcelery_email.tasks import send_emails
from djcelery_email.utils import chunked, email_to_dict


class CustomCeleryEmailBackend(CeleryEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        self.queue = kwargs.pop('queue', None)
        super(CeleryEmailBackend, self).__init__(fail_silently)
        self.init_kwargs = kwargs

    def send_messages(self, email_messages):
        result_tasks = []
        task_kwargs = {}
        if self.queue is not None:
            task_kwargs['queue'] = self.queue
        messages = [email_to_dict(msg) for msg in email_messages]
        for chunk in chunked(messages, settings.CELERY_EMAIL_CHUNK_SIZE):
            result_tasks.append(
                send_emails.apply_async(
                    args=[chunk],
                    kwargs={'backend_kwargs': self.init_kwargs},
                    **task_kwargs
                )
            )
        return result_tasks
