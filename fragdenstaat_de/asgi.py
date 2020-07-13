"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os
import django
from channels.routing import get_default_application

from configurations import importer
importer.install()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fragdenstaat_de.settings.production')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Production')

django.setup()
application = get_default_application()
