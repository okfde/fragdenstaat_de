# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import re

from django.utils.translation import ugettext_lazy as _

from froide.settings import Base, German


def rec(x):
    return re.compile(x, re.I | re.U)


def env(key, default=None):
    return os.environ.get(key, default)


THEME_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class FragDenStaatBase(German, Base):
    ROOT_URLCONF = 'fragdenstaat_de.theme.urls'

    LANGUAGES = (
        ('de', _('German')),
    )

    @property
    def INSTALLED_APPS(self):
        installed = super(FragDenStaatBase, self).INSTALLED_APPS
        installed.default = ['fragdenstaat_de.theme'] + installed.default + [
            'cms',
            'menus',
            'sekizai',

            'easy_thumbnails',
            'filer',
            'mptt',

            # Blog and dependencies
            'aldryn_apphooks_config',
            'cmsplugin_filer_image',
            'parler',
            'taggit_autosuggest',
            'meta',
            'sortedm2m',
            'djangocms_blog',

            # Newsletter and dependencies
            # 'sorl.thumbnail',
            # Customisations
            'fragdenstaat_de.fds_newsletter',

            'newsletter',

            # No longer needed when PR passes
            # https://github.com/divio/django-cms/pull/6564
            'overextends',

            'fragdenstaat_de.fds_cms',

            # Additional CMS plugins
            'djangocms_text_ckeditor',
            'djangocms_picture',
            'djangocms_video',

            'djcelery_email',
            'django.contrib.redirects',
            'tinymce',
            'markdown_deux',
            'raven.contrib.django.raven_compat',

            'froide_campaign.apps.FroideCampaignConfig',
            'froide_legalaction.apps.FroideLegalActionConfig',
            'froide_food.apps.FroideFoodConfig',
            'froide_fax.apps.FroideFaxConfig',
            'froide_exam'
        ]
        return installed.default

    @property
    def TEMPLATES(self):
        TEMP = super(FragDenStaatBase, self).TEMPLATES
        if 'DIRS' not in TEMP[0]:
            TEMP[0]['DIRS'] = []
        TEMP[0]['DIRS'] = [
            os.path.join(THEME_ROOT, 'theme', 'templates'),
        ] + list(TEMP[0]['DIRS'])
        TEMP[0]['OPTIONS']['builtins'] = ['overextends.templatetags.overextends_tags']
        cps = TEMP[0]['OPTIONS']['context_processors']
        cps.extend([
            'sekizai.context_processors.sekizai',
            'cms.context_processors.cms_settings',
        ])
        return TEMP

    # Newsletter

    NEWSLETTER_RICHTEXT_WIDGET = "tinymce.widgets.TinyMCE"
    DEFAULT_NEWSLETTER = 'fragdenstaat'

    # CMS

    CMS_TOOLBAR_ANONYMOUS_ON = False
    CMS_TEMPLATES = [
        ('cms/home.html', 'Homepage template'),
        ('cms/page.html', 'Page template'),
        ('cms/page_headerless.html', 'Page without header'),
        ('cms/blog_base.html', 'Blog base template'),
        ('cms/static_placeholders.html', 'Static Placeholder Overview'),
    ]
    DJANGOCMS_PICTURE_NESTING = True

    # Set to False until this is fixed
    # https://github.com/divio/django-cms/issues/5725
    CMS_PAGE_CACHE = False

    TEXT_ADDITIONAL_TAGS = ('iframe', 'embed',)
    TEXT_ADDITIONAL_ATTRIBUTES = ('scrolling', 'frameborder', 'webkitallowfullscreen',
                                  'mozallowfullscreen', 'allowfullscreen', 'sandbox', 'style')
    TEXT_ADDITIONAL_PROTOCOLS = ('bank',)

    CKEDITOR_SETTINGS = {
        'language': '{{ language }}',
        'skin': 'moono-lisa',
        'toolbar': 'CMS',
        'toolbarCanCollapse': False,
        'disableNativeSpellChecker': False,
        'extraPlugins': 'autocorrect',
        'autocorrect_replacementTable': {
            "...": "…",
        },
        'autocorrect_doubleQuotes': "„“",
        'entities': False,
        'stylesSet': 'default:/static/js/cms/ckeditor.wysiwyg.js',
    }

    DJANGOCMS_PICTURE_TEMPLATES = [
        ('hero', _('Hero'))
    ]

    BLOG_URLCONF = 'fragdenstaat_de.theme.blog_urls'
    BLOG_PAGINATION = 12
    BLOG_AVAILABLE_PERMALINK_STYLES = (
        ('full_date', _('Full date')),
        ('short_date', _('Year /  Month')),
        ('category', _('Category')),
        ('year_slug', _('Year + Slug')),
    )
    BLOG_PERMALINK_URLS = {
        'full_date': r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/(?P<slug>\w[-\w]*)/$',
        'short_date': r'^(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<slug>\w[-\w]*)/$',
        'category': r'^(?P<category>\w[-\w]*)/(?P<slug>\w[-\w]*)/$',
        'year_slug': r'^(?P<year>\d{4})/(?P<slug>\w[-\w]*)/$',
    }

    FILER_ENABLE_PERMISSIONS = True

    @property
    def FILER_STORAGES(self):
        MEDIA_ROOT = self.MEDIA_ROOT
        MEDIA_DOMAIN = ''
        if 'https://' in self.MEDIA_URL:
            MEDIA_DOMAIN = '/'.join(self.MEDIA_URL.split('/')[:3])
        return {
            'public': {
                'main': {
                    'ENGINE': 'filer.storage.PublicFileSystemStorage',
                    'OPTIONS': {
                        'location': os.path.join(MEDIA_ROOT, 'media/main'),
                        'base_url': self.MEDIA_URL + 'media/main/',
                    },
                    'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
                    'UPLOAD_TO_PREFIX': '',
                },
                'thumbnails': {
                    'ENGINE': 'filer.storage.PublicFileSystemStorage',
                    'OPTIONS': {
                        'location': os.path.join(MEDIA_ROOT, 'media/thumbnails'),
                        'base_url': self.MEDIA_URL + 'media/thumbnails/',
                    },
                    'THUMBNAIL_OPTIONS': {
                        'base_dir': '',
                    },
                },
            },
            'private': {
                'main': {
                    'ENGINE': 'filer.storage.PrivateFileSystemStorage',
                    'OPTIONS': {
                        'location': os.path.abspath(os.path.join(MEDIA_ROOT, '../private/main')),
                        'base_url': MEDIA_DOMAIN + '/smedia/main/',
                    },
                    'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
                    'UPLOAD_TO_PREFIX': '',
                },
                'thumbnails': {
                    'ENGINE': 'filer.storage.PrivateFileSystemStorage',
                    'OPTIONS': {
                        'location': os.path.abspath(os.path.join(MEDIA_ROOT, '../private/thumbnails')),
                        'base_url': MEDIA_DOMAIN + '/smedia/thumbnails/',
                    },
                    'UPLOAD_TO_PREFIX': '',
                },
            },
        }

    @property
    def FILER_SERVERS(self):
        FILER_STORAGES = self.FILER_STORAGES
        return {
            'private': {
                'main': {
                    'ENGINE': 'filer.server.backends.nginx.NginxXAccelRedirectServer',
                    'OPTIONS': {
                        'location': FILER_STORAGES['private']['main']['OPTIONS']['location'],
                        'nginx_location': '/private_main',
                    },
                },
                'thumbnails': {
                    'ENGINE': 'filer.server.backends.nginx.NginxXAccelRedirectServer',
                    'OPTIONS': {
                        'location': FILER_STORAGES['private']['thumbnails']['OPTIONS']['location'],
                        'nginx_location': '/private_thumbnails',
                    },
                },
            },
        }

    THUMBNAIL_PROCESSORS = (
        'easy_thumbnails.processors.colorspace',
        'easy_thumbnails.processors.autocrop',
        'filer.thumbnail_processors.scale_and_crop_with_subject_location',
        'easy_thumbnails.processors.filters',
    )
    META_SITE_PROTOCOL = 'http'
    META_USE_SITES = True

    @property
    def GEOIP_PATH(self):
        return os.path.join(super(FragDenStaatBase,
                            self).PROJECT_ROOT, '..', 'data')

    TINYMCE_DEFAULT_CONFIG = {
        'plugins': "table,spellchecker,paste,searchreplace",
        'theme': "advanced",
        'cleanup_on_startup': False
    }

    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'froide.helper.middleware.XForwardedForMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'fragdenstaat_de.theme.ilf_middleware.CsrfViewIlfMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
        'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
        'froide.account.middleware.AcceptNewTermsMiddleware',

        # 'django.middleware.locale.LocaleMiddleware',
        'cms.middleware.user.CurrentUserMiddleware',
        'cms.middleware.page.CurrentPageMiddleware',
        'cms.middleware.toolbar.ToolbarMiddleware',
        # 'cms.middleware.language.LanguageCookieMiddleware',
    ]

    CACHES = {
        'default': {
            'LOCATION': 'unique-snowflake',
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
        }
    }

    ELASTICSEARCH_INDEX_PREFIX = 'fragdenstaat_de'
    ELASTICSEARCH_DSL = {
        'default': {
            'hosts': 'localhost:9200'
        },
    }
    ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = 'froide.helper.search.CelerySignalProcessor'

    # ######### Debug ###########

    SITE_NAME = "FragDenStaat"
    SITE_EMAIL = "info@fragdenstaat.de"
    SITE_URL = 'http://localhost:8000'

    SECRET_URLS = {
        "admin": "admin",
    }

    ALLOWED_HOSTS = ('*',)
    ALLOWED_REDIRECT_HOSTS = ('*',)

    DEFAULT_FROM_EMAIL = 'FragDenStaat.de <info@fragdenstaat.de>'
    EMAIL_SUBJECT_PREFIX = '[AdminFragDenStaat] '

    EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
    CELERY_EMAIL_BACKEND = 'froide.foirequest.smtp.EmailBackend'
    CELERY_EMAIL_TASK_CONFIG = {
        'max_retries': None,
        'ignore_result': False,
        'acks_late': True,
        'store_errors_even_if_ignored': True
    }

    # Fig broker setup
    if 'BROKER_1_PORT' in os.environ:
        CELERY_BROKER_PORT = os.environ['BROKER_1_PORT'].replace('tcp://', '')
        BROKER_URL = 'amqp://guest:**@%s/' % CELERY_BROKER_PORT

    @property
    def FROIDE_CONFIG(self):
        config = super(FragDenStaatBase, self).FROIDE_CONFIG
        config.update(dict(
            create_new_publicbody=False,
            publicbody_empty=True,
            user_can_hide_web=True,
            public_body_officials_public=False,
            public_body_officials_email_public=False,
            default_law=2,
            doc_conversion_binary="/usr/bin/libreoffice",
            dryrun=False,
            read_receipt=True,
            delivery_receipt=True,
            dsn=True,
            message_handlers={
                'email': 'froide.foirequest.message_handlers.EmailMessageHandler',
                'fax': 'froide_fax.fax.FaxMessageHandler'
            },
            delivery_reporter='froide.foirequest.delivery.PostfixDeliveryReporter',
            search_text_analyzer='fragdenstaat_de.theme.search.get_text_analyzer',
            dryrun_domain="test.fragdenstaat.de",
            allow_pseudonym=True,
            api_activated=True,
            search_engine_query='http://www.google.de/search?as_q=%(query)s&as_epq=&as_oq=&as_eq=&hl=en&lr=&cr=&as_ft=i&as_filetype=&as_qdr=all&as_occt=any&as_dt=i&as_sitesearch=%(domain)s&as_rights=&safe=images',
            show_public_body_employee_name=False,
            request_throttle=[
                (5, 5 * 60),  # X requests in X seconds
                (10, 6 * 60 * 60),
                (15, 24 * 60 * 60),
                (30, 7 * 24 * 60 * 60),
            ],
            greetings=[
                rec(r"Sehr geehrte Damen und Herren,?"),
                rec(r"Sehr geehrt(er? (?:Herr|Frau)?(?: ?Dr\.?)?(?: ?Prof\.?)? .*)"),
            ],
            custom_replacements=[
                rec(r'[Bb][Gg]-[Nn][Rr]\.?\s*\:?\s*([a-zA-Z0-9\s/]+)')
            ],
            closings=[rec(r"([Mm]it )?(den )?(freundliche(n|m)?|vielen|besten)? ?Gr(ü|u)(ß|ss)(en?)?,?"), rec("Hochachtungsvoll,?"), rec(r'i\. ?A\.'), rec('[iI]m Auftrag')],
            content_urls={
                'terms': '/nutzungsbedingungen/',
                'privacy': '/datenschutzerklaerung/',
                'about': '/hilfe/ueber/',
                'help': '/hilfe/',
            },
            bounce_enabled=True,
            bounce_max_age=60 * 60 * 24 * 14,  # 14 days
            bounce_format='bounce+{token}@fragdenstaat.de',
            auto_reply_subject_regex=rec('^(Auto-?Reply|Out of office|Out of the office|Abwesenheitsnotiz|Automatische Antwort|automatische Empfangsbestätigung)'),
            auto_reply_email_regex=rec('^auto(reply|responder|antwort)@')
        ))
        return config

    FROIDE_FOOD_CONFIG = {
        'api_key_google': '',
        'api_key_yelp': os.environ.get('YELP_API_KEY', '')
    }

    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER', '')
