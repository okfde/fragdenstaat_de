import os
import sys

# Calculate the path based on the location of the WSGI script.
current_dir = os.path.dirname(__file__)
project = os.path.dirname(current_dir)

sys.path.append(project)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fragdenstaat_de.settings.production')
os.environ.setdefault('DJANGO_CONFIGURATION', 'FragDenStaat')

from django.conf import settings  # noqa
from configurations.wsgi import get_wsgi_application  # noqa

application = get_wsgi_application()

try:
    from whitenoise.django import DjangoWhiteNoise
    application = DjangoWhiteNoise(application)

    if settings.MEDIA_ROOT and settings.MEDIA_URL:
        application.add_files(settings.MEDIA_ROOT, prefix=settings.MEDIA_URL)
except ImportError:
    pass
