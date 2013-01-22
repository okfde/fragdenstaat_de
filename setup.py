#!/usr/bin/env python

from setuptools import setup

setup(
    name='FragDenStaat.de',
    version='1.0',
    description='Froide Theming for FragDenStaat.de',
    author='Stefan Wehrmeyer',
    author_email='stefan.wehrmeyer@okfn.org',
    url='https://fragdenstaat.de',
    packages=['fragdenstaat_de'],
    package_data={
        'fragdenstaat_de': [
            'templates/*',
            'locale/*/LC_MESSAGES/*',
            'static/*'
        ]
    },
)
