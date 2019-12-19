import os
import re

from django.utils.translation import ugettext_lazy as _

from froide.settings import Base, German


def rec(x):
    return re.compile(x, re.I | re.U | re.M)


def env(key, default=None):
    return os.environ.get(key, default)


THEME_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class FragDenStaatBase(German, Base):
    ROOT_URLCONF = 'fragdenstaat_de.theme.urls'

    LANGUAGES = (
        ('de', _('German')),
        ('en', _('English')),
    )

    @property
    def INSTALLED_APPS(self):
        installed = super(FragDenStaatBase, self).INSTALLED_APPS
        installed.default = ['fragdenstaat_de.theme'] + installed.default + [
            'cms',
            'menus',
            'sekizai',

            'easy_thumbnails',
            'easy_thumbnails.optimize',
            'filer',
            'mptt',
            'logentry_admin',

            'fragdenstaat_de.fds_blog',
            'adminsortable2',
            'parler',

            # Newsletter and dependencies
            # 'sorl.thumbnail',
            # Customisations
            'fragdenstaat_de.fds_newsletter',

            'newsletter',

            'fragdenstaat_de.fds_cms.apps.FdsCmsConfig',
            'fragdenstaat_de.fds_donation.apps.FdsDonationConfig',
            'fragdenstaat_de.fds_mailing.apps.FdsMailingConfig',

            # Additional CMS plugins
            'djangocms_text_ckeditor',
            'djangocms_picture',
            'djangocms_video',

            'djcelery_email',
            'django.contrib.redirects',
            'markdown_deux',
            'django_prices',

            'froide_campaign.apps.FroideCampaignConfig',
            'froide_legalaction.apps.FroideLegalActionConfig',
            'froide_payment.apps.FroidePaymentConfig',
            'froide_crowdfunding.apps.FroideCrowdfundingConfig',
            'froide_food.apps.FroideFoodConfig',
            'django_amenities.apps.AmenitiesConfig',
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
        cps = TEMP[0]['OPTIONS']['context_processors']
        cps.extend([
            'sekizai.context_processors.sekizai',
            'cms.context_processors.cms_settings',
            'fragdenstaat_de.theme.context_processors.theme_settings',
        ])
        return TEMP

    # Newsletter
    NEWSLETTER_RICHTEXT_WIDGET = 'djangocms_text_ckeditor.widgets.TextEditorWidget'
    DEFAULT_NEWSLETTER = 'fragdenstaat'
    DONOR_NEWSLETTER = 'spenden'

    # BLOG

    ARTICLE_CONTENT_TEMPLATES = [
        ('fds_blog/content/_article_no_image.html', _('No image in article'))
    ]
    ARTICLE_DETAIL_TEMPLATES = []

    LANGUAGE_COOKIE_AGE = 0

    PARLER_LANGUAGES = {
        1: (
            {'code': 'de'},
            {'code': 'en'},
        ),
        'default': {
            'hide_untranslated': False,   # the default; let .active_translations() return fallbacks too.
        }
    }

    # CMS

    CMS_LANGUAGES = {
        # Customize this
        'default': {
            'public': True,
            'hide_untranslated': False,
            'redirect_on_fallback': True,
            'fallbacks': ['en', 'de'],
        },
        1: [
            {
                'public': True,
                'code': 'de',
                'hide_untranslated': False,
                'name': _('German'),
                'redirect_on_fallback': True,
            },
            {
                'public': True,
                'code': 'en',
                'hide_untranslated': False,
                'name': _('English'),
                'redirect_on_fallback': True,
            }
        ],
    }

    CMS_TOOLBAR_ANONYMOUS_ON = False
    CMS_TEMPLATES = [
        ('cms/home.html', 'Homepage template'),
        ('cms/page.html', 'Page template'),
        ('cms/page_headerless.html', 'Page without header'),
        ('cms/page_reduced.html', 'Page reduced'),
        ('cms/blog_base.html', 'Blog base template'),
        ('cms/static_placeholders.html', 'Static Placeholder Overview'),
    ]
    CMS_PLACEHOLDER_CONF = {
        'email_body': {
            'plugins': [
                'TextPlugin', 'EmailActionPlugin',
                'EmailSectionPlugin', 'EmailStoryPlugin',
                'EmailBodyPlugin', 'EmailHeaderPlugin'
            ],
            'text_only_plugins': [],
            'name': _('E-Mail Body'),
            'language_fallback': True,
            'default_plugins': [],
            'child_classes': {},
            'parent_classes': {},
        }
    }
    CMS_PLUGIN_CONTEXT_PROCESSORS = [
        'fragdenstaat_de.fds_mailing.utils.add_style'
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
        'toolbar_CMS': [
            ['Undo', 'Redo'],
            ['cmsplugins', '-'],
            ['Format', 'Styles'],
            [
                'TextColor', 'BGColor', '-',
                'PasteText', 'PasteFromWord'
            ],
            # ['Scayt'],
            ['Maximize', ''],
            '/',
            ['Bold', 'Italic', 'Underline', 'Strike', '-', 'Subscript', 'Superscript', '-', 'RemoveFormat'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['HorizontalRule'],
            ['NumberedList', 'BulletedList'],
            ['Outdent', 'Indent', '-', 'Blockquote', '-', 'Link', 'Unlink', '-', 'Table', 'CreateDiv'],
            ['ShowBlocks', 'Source']
        ],
        'toolbarCanCollapse': False,
        'disableNativeSpellChecker': False,
        'extraPlugins': 'autocorrect',
        'autocorrect_replacementTable': {
            "...": "…",
        },
        'removePlugins': 'contextmenu',  # liststyle,tabletools,tableselection',
        'autocorrect_doubleQuotes': "„“",
        'disableNativeSpellChecker': False,
        'entities': False,
        'stylesSet': 'default:/static/js/cms/ckeditor.wysiwyg.js',
        'contentsCss': '/static/css/main.css',
    }

    DJANGOCMS_PICTURE_TEMPLATES = [
        ('hero', _('Hero'))
    ]

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

    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'froide.helper.middleware.XForwardedForMiddleware',
        'django.middleware.locale.LocaleMiddleware',  # needs to be before CommonMiddleware
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'fragdenstaat_de.theme.ilf_middleware.CsrfViewIlfMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
        'fragdenstaat_de.theme.redirects.PathRedirectFallbackMiddleware',
        'froide.account.middleware.AcceptNewTermsMiddleware',

        'cms.middleware.user.CurrentUserMiddleware',
        'cms.middleware.page.CurrentPageMiddleware',
        'cms.middleware.toolbar.ToolbarMiddleware',
        'fragdenstaat_de.theme.cms_utils.HostLanguageCookieMiddleware',
    ]
    FROIDE_CSRF_MIDDLEWARE = 'fragdenstaat_de.theme.ilf_middleware.CsrfViewIlfMiddleware'

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

    DEFAULT_CURRENCY = 'EUR'
    DEFAULT_DECIMAL_PLACES = 2
    PAYMENT_HOST = 'localhost:8000'
    PAYMENT_USES_SSL = False
    PAYMENT_MODEL = 'froide_payment.Payment'
    PAYMENT_VARIANTS = {
        'lastschrift': ('froide_payment.provider.LastschriftProvider', {}),
        'banktransfer': ('froide_payment.provider.BanktransferProvider', {}),
        'default': ('payments.dummy.DummyProvider', {})
    }

    EMAIL_BACKEND = 'fragdenstaat_de.theme.email_backend.CustomCeleryEmailBackend'
    CELERY_EMAIL_BACKEND = 'froide.foirequest.smtp.EmailBackend'
    CELERY_EMAIL_TASK_CONFIG = {
        'max_retries': None,
        'ignore_result': False,
        'acks_late': True,
        'store_errors_even_if_ignored': True
    }

    if 'DJANGO_CELERY_BROKER_URL' in os.environ:
        CELERY_BROKER_URL = env('DJANGO_CELERY_BROKER_URL')

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
            text_analyzer='fragdenstaat_de.theme.search.get_text_analyzer',
            search_analyzer='fragdenstaat_de.theme.search.get_search_analyzer',
            search_quote_analyzer='fragdenstaat_de.theme.search.get_search_quote_analyzer',
            dryrun_domain="test.fragdenstaat.de",
            allow_pseudonym=True,
            api_activated=True,
            search_engine_query='http://www.google.de/search?as_q=%(query)s&as_epq=&as_oq=&as_eq=&hl=en&lr=&cr=&as_ft=i&as_filetype=&as_qdr=all&as_occt=any&as_dt=i&as_sitesearch=%(domain)s&as_rights=&safe=images',
            show_public_body_employee_name=False,
            request_throttle=[
                (5, 5 * 60),  # X requests in X seconds
                (6, 6 * 60 * 60),
                (10, 24 * 60 * 60),
                (20, 7 * 24 * 60 * 60),
            ],
            greetings=[
                # Important: always needs to capture name to be removed
                rec(r"^\s*Name des Absenders\s+(.*)"),
                rec(r"^\s*Sehr geehrte Damen und Herren,?"),
                rec(r"^\s*Hallo\s+(.*)"),
                rec(r"^\s*Lieber?\s+(.*)"),
                rec(r"^\s*Sehr (?:Herr|Frau|Fr\.|Hr\.) (.*)"),
                rec(r"^\s*Sehr geehrte(.*)"),
                rec(r"^\s*Sehr geehrt(er? (?:Herr|Frau|Fr\.|Hr\.)?(?: ?Dr\.?)?(?: ?Prof\.?)? .*)"),
                rec(r"^\s*(?:Von|An|Cc|To|From): (.*)"),
            ],
            custom_replacements=[
                rec(r'[Bb][Gg]-[Nn][Rr]\.?\s*\:?\s*([a-zA-Z0-9\s/]+)'),
                rec(r'Ihr Kennwort lautet: (.*)')
            ],
            closings=[
                rec(r"([Mm]it )?(den )?(freundliche(n|m)?|vielen|besten)? ?Gr(ü|u|\?)(ß|ss|\?)(en?)?,?"),
                rec("Hochachtungsvoll,?"),
                rec(r'i\. ?A\.'),
                rec(r'[iI]m Auftrag'),
                rec(r"(?:Best regards|Kind regards|Sincerely),?")
            ],
            hide_content_funcs=[
                # Hide DHL delivery emails
                lambda email: email.from_[1] == 'noreply@dhl.com'
            ],
            recipient_blacklist_regex=rec(r'.*\.de-mail\.de$|z@bundesnachrichtendienst.de|.*\.local$'),
            content_urls={
                'terms': '/nutzungsbedingungen/',
                'privacy': '/datenschutzerklaerung/',
                'about': '/hilfe/ueber/',
                'help': '/hilfe/',
            },
            bounce_enabled=True,
            bounce_max_age=60 * 60 * 24 * 14,  # 14 days
            bounce_format='bounce+{token}@fragdenstaat.de',
            unsubscribe_enabled=True,
            unsubscribe_format='unsub+{token}@fragdenstaat.de',
            auto_reply_subject_regex=rec('^(Auto-?Reply|Out of office|Out of the office|Abwesenheitsnotiz|Automatische Antwort|automatische Empfangsbestätigung)'),
            auto_reply_email_regex=rec('^auto(reply|responder|antwort)@')
        ))
        return config

    FROIDE_FOOD_CONFIG = {
        'api_key_google': os.environ.get('GOOGLE_PLACES_API_KEY'),
        'api_key_geocode_here': os.environ.get('HERE_GEOCODE_API_KEY'),
        'api_key_geocode_mapbox': os.environ.get('MAPBOX_API_KEY'),
        'api_key_yelp': os.environ.get('YELP_API_KEY', ''),
        'api_key_foursquare': os.environ.get('FOURSQUARE_API_KEY')
    }

    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
    TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER', '')

    SLACK_DEFAULT_CHANNEL = os.environ.get(
        'SLACK_DEFAULT_CHANNEL', 'fragdenstaat-alerts'
    )
    SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')

    SENTRY_JS_URL = ''
