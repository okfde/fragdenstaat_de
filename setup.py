#!/usr/bin/env python

from __future__ import print_function

import os
import re
import codecs

from setuptools import setup, find_packages


def read(*parts):
    filename = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(filename, encoding='utf-8') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="fragdenstaat_de",
    version=find_version("fragdenstaat_de", "__init__.py"),
    url='https://github.com/okfde/fragdenstaat_de',
    license='AGPL',
    description="FragDenStaat.de theme for Froide install",
    long_description=read('README.md'),
    author='Stefan Wehrmeyer',
    author_email='mail@stefanwehrmeyer.com',
    packages=find_packages(),
    install_requires=[
        'froide',
        'froide-campaign',
        'froide-food',
        'froide-fax',
        'froide-exam',
        'froide-legalaction',
        'django-filingcabinet',

        'django<2.0',
        'markdown',
        'celery',
        'django-celery-email',
        'django-taggit',
        'pytz',
        'requests',
        'django-floppyforms',
        'python-magic',
        'python-mimeparse>=0.1.4',
        'django-configurations',
        'django-storages',
        'dj-database-url',
        'django-cache-url',
        'django-contrib-comments',
        'honcho',
        'django-tinymce',
        'anyjson',
        'psycopg2-binary',
        'raven',
        'python-memcached',
        'pypdf2',
        'reportlab',
        'wand',
        'djangorestframework',
        'django-oauth-toolkit<1.2.0',
        'coreapi',
        'django-filter',
        'django-cms==3.5.3',
        'django-filer',
        'djangocms-text-ckeditor==3.6.1',
        'djangocms-picture',
        'djangocms-video',
        'python-slugify',
        'django-leaflet',
        'phonenumbers',
        'django-treebeard',
        'djangocms-blog',
        'aldryn-apphooks-config==0.4.1',
        'djangorestframework-jsonp',
        'geoip2',
        'pdflib',
        'pylatex',
        'twilio',
        'djangorestframework-csv',
        'pyisemail',
        'icalendar',
        'django-newsletter',
    ],
    include_package_data=True,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: AGPL License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities',
    ],
    zip_safe=False,
)
