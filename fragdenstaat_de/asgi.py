"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os
import django
from channels.routing import get_default_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fragdenstaat_de.settings.development')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Dev')

from configurations import importer
importer.install()

django.setup()
application = get_default_application()
