#!/usr/bin/env python

from __future__ import print_function

import codecs
import os
import re

from setuptools import find_packages, setup


def read(*parts):
    filename = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(filename, encoding="utf-8") as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


extras = {
    "lint": ["flake8"],
}


setup(
    name="fragdenstaat_de",
    version=find_version("fragdenstaat_de", "__init__.py"),
    url="https://github.com/okfde/fragdenstaat_de",
    license="AGPL",
    description="FragDenStaat.de theme for Froide install",
    long_description=read("README.md"),
    author="Stefan Wehrmeyer",
    author_email="mail@stefanwehrmeyer.com",
    packages=find_packages(),
    install_requires=[
        "froide",
        "froide-campaign",
        "froide-food",
        "froide-fax",
        "froide-exam",
        "froide-payment",
        "froide-crowdfunding",
        "froide-legalaction",
        "django-filingcabinet",
        "django",
        "markdown",
        "celery",
        "django-celery-email",
        "django-taggit",
        "pytz",
        "requests",
        "django-floppyforms",
        "python-magic",
        "python-mimeparse",
        "django-configurations",
        "django-contractor",
        "django-crossdomainmedia",
        "django-storages",
        "dj-database-url",
        "django-cache-url",
        "django-contrib-comments",
        "psycopg2",
        "sentry-sdk",
        "pypdf2",
        "reportlab",
        "wand",
        "djangorestframework",
        "django-oauth-toolkit",
        "coreapi",
        "django-filter",
        "django-cms",
        "django-filer",
        "djangocms-text-ckeditor",
        "djangocms-picture",
        "djangocms-video",
        "python-slugify",
        "django-leaflet",
        "phonenumbers",
        "num2words",
        "django-treebeard",
        "djangorestframework-jsonp",
        "geoip2",
        "pandas",
        "djangorestframework-csv",
        "pyisemail",
        "icalendar",
        "django-newsletter",
        "xlrd",
    ],
    extras_require=extras,
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: AGPL License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Topic :: Utilities",
    ],
    zip_safe=False,
)
