import os
import re
from datetime import timedelta
from pathlib import Path

from django.templatetags.static import static
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _

from configurations import values

from froide.settings import Base, German


def rec(x):
    return re.compile(x, re.I | re.U | re.M)


def env(key, default=None):
    return os.environ.get(key, default)


THEME_ROOT = Path(__file__).resolve().parent.parent


class FragDenStaatBase(German, Base):
    ROOT_URLCONF = "fragdenstaat_de.theme.urls"
    ASGI_APPLICATION = "fragdenstaat_de.routing.application"

    LANGUAGES = (
        ("de", _("German")),
        ("en", _("English")),
    )

    @property
    def INSTALLED_APPS(self):
        installed = super(FragDenStaatBase, self).INSTALLED_APPS
        installed.default = (
            [
                "fragdenstaat_de.theme",
            ]
            + installed.default
            + [
                "django.contrib.postgres",
                "fragdenstaat_de.fds_cms.apps.FdsCmsConfig",
                "djangocms_versioning",
                "cms",
                "djangocms_alias",
                "menus",
                "sekizai",
                # "djangocms_transfer",
                # easy thumbnails comes from froide
                "filer",
                "logentry_admin",
                "localflavor",
                "fragdenstaat_de.fds_blog",
                "adminsortable2",
                # Customisations
                "fragdenstaat_de.fds_newsletter",
                "fragdenstaat_de.fds_donation.apps.FdsDonationConfig",
                "fragdenstaat_de.fds_mailing.apps.FdsMailingConfig",
                "fragdenstaat_de.fds_ogimage.apps.FdsOgImageConfig",
                "fragdenstaat_de.fds_fximport.apps.FdsFxImportConfig",
                "fragdenstaat_de.fds_paperless",
                "fragdenstaat_de.fds_events",
                # Additional CMS plugins
                "djangocms_text",
                "djangocms_text.contrib.text_ckeditor4",
                "djangocms_picture",
                "djangocms_video",
                "djangocms_audio",
                "djangocms_icon",
                "djangocms_link",
                "djangocms_frontend",
                "djangocms_frontend.contrib.accordion",
                "djangocms_frontend.contrib.alert",
                "djangocms_frontend.contrib.badge",
                "djangocms_frontend.contrib.card",
                "djangocms_frontend.contrib.carousel",
                "djangocms_frontend.contrib.collapse",
                "djangocms_frontend.contrib.content",
                "djangocms_frontend.contrib.grid",
                # We use djangocms_picture instead
                # "djangocms_frontend.contrib.image",
                "djangocms_frontend.contrib.jumbotron",
                "djangocms_frontend.contrib.link",
                "djangocms_frontend.contrib.listgroup",
                "djangocms_frontend.contrib.media",
                "djangocms_frontend.contrib.tabs",
                "djangocms_frontend.contrib.utilities",
                # Additional CMS plugins
                "sortabletable",
                "contractor",
                "datashow",
                "djcelery_email",
                "django.contrib.redirects",
                "froide_campaign.apps.FroideCampaignConfig",
                "froide_legalaction.apps.FroideLegalActionConfig",
                "froide_payment.apps.FroidePaymentConfig",
                "froide_crowdfunding.apps.FroideCrowdfundingConfig",
                "froide_food.apps.FroideFoodConfig",
                "django_amenities.apps.AmenitiesConfig",
                "froide_fax.apps.FroideFaxConfig",
                "froide_exam",
                "froide_govplan.apps.FroideGovPlanConfig",
                "froide_evidencecollection.apps.FroideEvidencecollectionConfig",
                "legal_advice_builder.apps.LegalAdviceBuilderConfig",
                "fcdocs_annotate.annotation.apps.AnnotationConfig",
                "tinymce",
                "cookie_consent",
            ]
        )
        return installed.default

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "overwrite": {
            # Replace in Django 5.1 with allow_overwrite Option
            "BACKEND": "froide.helper.storage.OverwriteStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

    @property
    def TEMPLATES(self):
        TEMP = super().TEMPLATES
        if "DIRS" not in TEMP[0]:
            TEMP[0]["DIRS"] = []
        TEMP[0]["DIRS"] = [
            THEME_ROOT / "templates",
        ] + list(TEMP[0]["DIRS"])
        cps = TEMP[0]["OPTIONS"]["context_processors"]
        cps.extend(
            [
                "sekizai.context_processors.sekizai",
                "cms.context_processors.cms_settings",
                "fragdenstaat_de.theme.context_processors.theme_settings",
            ]
        )
        return TEMP

    @property
    def LOCALE_PATHS(self):
        locales = list(super().LOCALE_PATHS)
        return [
            THEME_ROOT / "locale",
        ] + locales

    STATIC_ROOT = values.Value(THEME_ROOT.parent / "public")
    FRONTEND_BUILD_DIR = THEME_ROOT.parent / "build"

    @property
    def STATICFILES_DIRS(self):
        return [THEME_ROOT / "static"] + super().STATICFILES_DIRS

    # Newsletter
    DEFAULT_NEWSLETTER = "fragdenstaat"
    DONOR_NEWSLETTER = "spenden"

    def three_days_ago_but_not_sundays(date):
        """
        return tuple of gte and lt dates
        """
        weekday = date.weekday()
        if weekday == 6:
            # empty filter on Sunday
            return (date, date)
        elif weekday == 5:
            # on Saturday, send Wednesday and Thursday subscribers
            return (date - timedelta(days=3), date - timedelta(days=1))
        # Otherwise send three days ago subscribers
        return (date - timedelta(days=3), date - timedelta(days=2))

    NEWSLETTER_WELCOME_MAILINTENT = {DEFAULT_NEWSLETTER: "fds_newsletter/email/welcome"}
    NEWSLETTER_ONBOARDING_SCHEDULE = [
        {
            "newsletter": DEFAULT_NEWSLETTER,
            "mail_intent": "fds_newsletter/email/intro",
            "date": three_days_ago_but_not_sundays,
        }
    ]
    NEWSLETTER_PIXEL_ORIGIN = env("NEWSLETTER_PIXEL_ORIGIN", "http://localhost:8000")
    NEWSLETTER_PIXEL_LOG = env("NEWSLETTER_PIXEL_LOG", "/var/log/pixel.log")

    # Campaign

    CAMPAIGN_PROVIDERS = [
        ("", "froide_campaign.providers.informationobject.InformationObjectProvider"),
        ("amenity", "froide_campaign.providers.amenity.AmenityProvider"),
        ("publicbody", "froide_campaign.providers.publicbody.PublicBodyProvider"),
        (
            "amenity_local",
            "froide_campaign.providers.amenity_local.AmenityLocalProvider",
        ),
    ]

    # BLOG

    ARTICLE_CONTENT_TEMPLATES = [
        ("fds_blog/content/_article_no_image.html", _("No image in article")),
        ("fds_blog/content/_article_video_header.html", _("Video header")),
    ]
    ARTICLE_DETAIL_TEMPLATES = []

    PARLER_LANGUAGES = {
        1: (
            {"code": "de"},
            {"code": "en"},
        ),
        "default": {
            # the default; let .active_translations() return fallbacks too.
            "hide_untranslated": False,
        },
    }

    # CMS

    CMS_PERMISSION = True
    CMS_RAW_ID_USERS = True
    CMS_CONFIRM_VERSION4 = True
    CMS_MIGRATION_USER_ID = 1

    CMS_LANGUAGES = {
        # Customize this
        "default": {
            "public": True,
            "hide_untranslated": True,
            "redirect_on_fallback": True,
            "fallbacks": [],
        },
        1: [
            {
                "public": True,
                "code": "de",
                "hide_untranslated": True,
                "name": _("German"),
                "redirect_on_fallback": True,
            },
            {
                "public": True,
                "code": "en",
                "hide_untranslated": True,
                "name": _("English"),
                "redirect_on_fallback": True,
                "fallbacks": ["de"],
            },
        ],
    }

    CMS_SIDEFRAME_ENABLED = False
    CMS_TOOLBAR_ANONYMOUS_ON = False
    CMS_TEMPLATES = [
        ("cms/home.html", "Homepage template"),
        ("cms/page.html", "Page template"),
        ("cms/page_headerless.html", "Page without header"),
        ("cms/page_reduced.html", "Page reduced"),
        ("cms/page_minimal.html", "Page minimal"),
        ("cms/page_breadcrumb.html", "Page with breadcrumbs"),
        ("cms/blog_base.html", "Blog base template"),
        ("cms/help_base.html", "Help base template"),
        ("cms/pub_base.html", "Book Publication template"),
        ("froide_govplan/base.html", "Govplan base template"),
        ("cms/page_anon.html", "Page without tracking"),
        ("cmssites/cmssite/gegenrechtsschutz.html", "Gegenrechtsschutz Template"),
    ]
    EMAIL_BODY_PLUGINS = [
        "IsDonorPlugin",
        "IsNotDonorPlugin",
        "IsRecurringDonorPlugin",
        "IsNotRecurringDonorPlugin",
        "IsRecentDonor",
        "IsNotRecentDonor",
        "ContactAllowedDonor",
        "ContactNotAllowedDonor",
        "IsNewsletterSubscriberPlugin",
        "IsNotNewsletterSubscriberPlugin",
        "EmailDonationButtonPlugin",
        "TextPlugin",
        "EmailActionPlugin",
        "EmailSectionPlugin",
        "EmailStoryPlugin",
        "EmailHeaderPlugin",
        "PicturePlugin",
        "EmailButtonPlugin",
        "ConditionPlugin",
    ]
    CMS_PLACEHOLDER_CONF = {
        "email_body": {
            "plugins": [
                "EmailBodyPlugin",
            ]
            + EMAIL_BODY_PLUGINS,
            "text_only_plugins": [],
            "name": _("E-Mail Body"),
            "language_fallback": True,
            "default_plugins": [],
            "child_classes": {},
            "parent_classes": {},
        }
    }
    CMS_PLUGIN_CONTEXT_PROCESSORS = ["fragdenstaat_de.fds_mailing.utils.add_style"]

    DJANGOCMS_PICTURE_NESTING = True

    CMS_PAGE_CACHE = True  # Workaround in fds_cms/models.py
    CMS_COLOR_SCHEME_TOGGLE = True
    CMS_COLOR_SCHEME = "auto"
    # Automatically redirect to the lowercase version of a slug if a cms page is
    # not found https://github.com/django-cms/django-cms/pull/7509/files
    CMS_REDIRECT_TO_LOWERCASE_SLUG = True

    TEXT_ADDITIONAL_ATTRIBUTES = {
        "iframe": {
            "scrolling",
            "frameborder",
            "webkitallowfullscreen",
            "mozallowfullscreen",
            "allowfullscreen",
            "sandbox",
            "src",
            "style",
            "class",
            "id",
        },
        "embed": {"type", "src", "width", "height"},
        "summary": {"class"},
        "details": {"class", "open"},
        "*": {"style", "class", "id"},
    }

    TEXT_EDITOR = "fragdenstaat_de.theme.editor.ckeditor4"

    CKEDITOR_SETTINGS = {
        "language": "{{ language }}",
        "skin": "moono-lisa",
        "toolbar": "CMS",
        "toolbar_CMS": [
            ["Undo", "Redo"],
            ["CMSPlugins", "-"],
            ["Format", "Styles"],
            ["TextColor", "BGColor", "-", "PasteText", "PasteFromWord"],
            # ['Scayt'],
            ["Maximize", ""],
            "/",
            [
                "Bold",
                "Italic",
                "Underline",
                "Strike",
                "-",
                "Subscript",
                "Superscript",
                "-",
                "RemoveFormat",
            ],
            ["JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"],
            ["HorizontalRule"],
            ["NumberedList", "BulletedList"],
            [
                "Outdent",
                "Indent",
                "-",
                "figureblockquote",
                "-",
                "Link",
                "Unlink",
                "-",
                "Table",
                "CreateDiv",
            ],
            ["ShowBlocks", "Source"],
        ],
        "toolbarCanCollapse": False,
        "extraPlugins": "autocorrect,figureblockquote",
        "autocorrect_replacementTable": {
            "...": "…",
        },
        "removePlugins": "contextmenu,liststyle,tabletools,tableselection",
        "autocorrect_doubleQuotes": "„“",
        "disableNativeSpellChecker": False,
        "entities": False,
        # "stylesSet": "default:/static/js/cms/ckeditor.wysiwyg.js",
        "contentsCss": lazy(static, str)("css/main.css"),
        "height": "500px",
    }

    DJANGOCMS_PICTURE_TEMPLATES = [("hero", _("Hero")), ("email", _("Email"))]

    TINYMCE_DEFAULT_CONFIG = {
        "theme": "silver",
        "height": 500,
        "menubar": False,
        "plugins": (
            "autolink,lists,link,charmap,print,preview,anchor,"
            "searchreplace,visualblocks,code,fullscreen,paste,"
            "code,wordcount"
        ),
        "toolbar": (
            "undo redo | h3 h4 h5 | "
            "bold italic | link | bullist numlist blockquote | "
            "removeformat visualblocks code"
        ),
    }

    FILER_ENABLE_PERMISSIONS = True

    @property
    def FILER_STORAGES(self):
        MEDIA_ROOT = self.MEDIA_ROOT
        MEDIA_DOMAIN = ""
        if "https://" in self.MEDIA_URL:
            MEDIA_DOMAIN = "/".join(self.MEDIA_URL.split("/")[:3])
        return {
            "public": {
                "main": {
                    "ENGINE": "filer.storage.PublicFileSystemStorage",
                    "OPTIONS": {
                        "location": os.path.join(MEDIA_ROOT, "media/main"),
                        "base_url": self.MEDIA_URL + "media/main/",
                    },
                    "UPLOAD_TO": "filer.utils.generate_filename.randomized",
                    "UPLOAD_TO_PREFIX": "",
                },
                "thumbnails": {
                    "ENGINE": "filer.storage.PublicFileSystemStorage",
                    "OPTIONS": {
                        "location": os.path.join(MEDIA_ROOT, "media/thumbnails"),
                        "base_url": self.MEDIA_URL + "media/thumbnails/",
                    },
                    "THUMBNAIL_OPTIONS": {
                        "base_dir": "",
                    },
                },
            },
            "private": {
                "main": {
                    "ENGINE": "filer.storage.PrivateFileSystemStorage",
                    "OPTIONS": {
                        "location": os.path.abspath(
                            os.path.join(MEDIA_ROOT, "../private/main")
                        ),
                        "base_url": MEDIA_DOMAIN + "/smedia/main/",
                    },
                    "UPLOAD_TO": "filer.utils.generate_filename.randomized",
                    "UPLOAD_TO_PREFIX": "",
                },
                "thumbnails": {
                    "ENGINE": "filer.storage.PrivateFileSystemStorage",
                    "OPTIONS": {
                        "location": os.path.abspath(
                            os.path.join(MEDIA_ROOT, "../private/thumbnails")
                        ),
                        "base_url": MEDIA_DOMAIN + "/smedia/thumbnails/",
                    },
                    "UPLOAD_TO_PREFIX": "",
                },
            },
        }

    @property
    def FILER_SERVERS(self):
        FILER_STORAGES = self.FILER_STORAGES
        return {
            "private": {
                "main": {
                    "ENGINE": "filer.server.backends.nginx.NginxXAccelRedirectServer",
                    "OPTIONS": {
                        "location": FILER_STORAGES["private"]["main"]["OPTIONS"][
                            "location"
                        ],
                        "nginx_location": "/private_main",
                    },
                },
                "thumbnails": {
                    "ENGINE": "filer.server.backends.nginx.NginxXAccelRedirectServer",
                    "OPTIONS": {
                        "location": FILER_STORAGES["private"]["thumbnails"]["OPTIONS"][
                            "location"
                        ],
                        "nginx_location": "/private_thumbnails",
                    },
                },
            },
        }

    THUMBNAIL_PROCESSORS = (
        "easy_thumbnails.processors.colorspace",
        "easy_thumbnails.processors.autocrop",
        "filer.thumbnail_processors.scale_and_crop_with_subject_location",
        "easy_thumbnails.processors.filters",
    )
    THUMBNAIL_PRESERVE_EXTENSIONS = (
        "png",
        "svg",
    )

    THUMBNAIL_DEFAULT_ALIAS = "default"
    THUMBNAIL_ALIASES = {
        "filer.Image": {
            "colmd4": {"size": (260, 0)},
            "colmd6": {"size": (380, 0)},
            "smcontainer": {
                "size": (520, 0)
            },  # 516px = sm container - padding ; 2x small
            THUMBNAIL_DEFAULT_ALIAS: {"size": (768, 0)},
            "lgcontainer": {
                "size": (940, 0)
            },  # 936px = lg container - padding, but 940 exists already
            "xlcontainer": {
                "size": (1140, 0)
            },  # 1116px = xl container - padding, but 1140 exists already
            "xxlcontainer": {"size": (1296, 0)},
            "lgcontainer@2x": {"size": (1872, 0)},
            "xlcontainer@2x": {"size": (2232, 0)},
            "xxlcontainer@2x": {"size": (2592, 0)},
            "xxxl": {"size": (3840, 0)},
        },
    }
    FDS_THUMBNAIL_ENABLE_AVIF = False

    META_SITE_PROTOCOL = "http"
    META_USE_SITES = True

    @property
    def GEOIP_PATH(self):
        return os.path.join(super(FragDenStaatBase, self).PROJECT_ROOT, "..", "data")

    GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH")
    GEOS_LIBRARY_PATH = os.environ.get("GEOS_LIBRARY_PATH")

    FROIDE_CSRF_MIDDLEWARE = "django.middleware.csrf.CsrfViewMiddleware"
    MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        "froide.helper.middleware.XForwardedForMiddleware",
        "django.middleware.locale.LocaleMiddleware",  # needs to be before CommonMiddleware
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        FROIDE_CSRF_MIDDLEWARE,
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "fragdenstaat_de.theme.middleware.XFrameOptionsCSPMiddleware",
        "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
        "fragdenstaat_de.theme.redirects.PathRedirectFallbackMiddleware",
        "froide.account.middleware.AcceptNewTermsMiddleware",
        "cms.middleware.user.CurrentUserMiddleware",
        "cms.middleware.page.CurrentPageMiddleware",
        "cms.middleware.toolbar.ToolbarMiddleware",
        "fragdenstaat_de.theme.cms_utils.HostLanguageCookieMiddleware",
    ]

    CACHES = {
        "default": {
            "LOCATION": "unique-snowflake",
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

    ELASTICSEARCH_INDEX_PREFIX = "fragdenstaat_de"
    ELASTICSEARCH_DSL = {
        "default": {"hosts": "http://localhost:9200"},
    }
    ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = "froide.helper.search.CelerySignalProcessor"

    # ######### Debug ###########

    SITE_NAME = "FragDenStaat"
    SITE_LOGO = (
        "https://media.frag-den-staat.de/files/media/main/f9/21/"
        "f9211ce7-9924-47da-913f-3070dbd4d298/og-default-sm.png"
    )
    SITE_EMAIL = "info@fragdenstaat.de"
    SITE_URL = "http://localhost:8000"

    SECRET_URLS = {
        "admin": "admin",
    }

    ALLOWED_HOSTS = ("*",)
    ALLOWED_REDIRECT_HOSTS = ("*",)

    CREW_GROUP = 13

    @property
    def OAUTH2_PROVIDER(self):
        P = super().OAUTH2_PROVIDER
        P["ALLOWED_REDIRECT_URI_SCHEMES"] = ["https", "fragdenstaat"]
        return P

    DEFAULT_FROM_EMAIL = "FragDenStaat.de <info@fragdenstaat.de>"
    EMAIL_SUBJECT_PREFIX = "[AdminFragDenStaat] "

    DEFAULT_CURRENCY = "EUR"
    DEFAULT_DECIMAL_PLACES = 2
    PAYMENT_HOST = "localhost:8000"
    PAYMENT_USES_SSL = False
    PAYMENT_MODEL = "froide_payment.Payment"
    PAYMENT_VARIANTS = {
        "lastschrift": ("froide_payment.provider.LastschriftProvider", {}),
        "banktransfer": ("froide_payment.provider.BanktransferProvider", {}),
        "default": ("payments.dummy.DummyProvider", {}),
    }
    PAYMENT_CHECK_THRESHOLD = int(env("PAYMENT_CHECK_THRESHOLD", "1000"))
    DONATION_PROJECTS = [
        ("FDS", "FragDenStaat"),  # First project becomes default project
        ("CFG", "Code for Germany"),
        ("JH", "Jugend hackt"),
        ("GM", "Gemeinkosten"),
    ]
    DONATION_BACKUP_URL = env("DONATION_BACKUP_URL")
    DONATION_BACKUP_CREDENTIALS = env("DONATION_BACKUP_CREDENTIALS")

    FDS_LEGAL_BACKUP_URL = env("FDS_LEGAL_BACKUP_URL")
    FDS_LEGAL_BACKUP_CREDENTIALS = env("FDS_LEGAL_BACKUP_CREDENTIALS")

    EMAIL_BACKEND = "fragdenstaat_de.theme.email_backend.CustomCeleryEmailBackend"
    CELERY_EMAIL_BACKEND = "froide.foirequest.smtp.EmailBackend"
    CELERY_EMAIL_TASK_CONFIG = {
        "max_retries": None,
        "ignore_result": False,
        "acks_late": True,
        "store_errors_even_if_ignored": True,
    }

    if "DJANGO_CELERY_BROKER_URL" in os.environ:
        CELERY_BROKER_URL = env("DJANGO_CELERY_BROKER_URL")

    # Fig broker setup
    if "BROKER_1_PORT" in os.environ:
        CELERY_BROKER_PORT = os.environ["BROKER_1_PORT"].replace("tcp://", "")
        BROKER_URL = "amqp://guest:**@%s/" % CELERY_BROKER_PORT

    @property
    def FROIDE_CONFIG(self):
        config = super(FragDenStaatBase, self).FROIDE_CONFIG
        config.update(
            {
                "create_new_publicbody": False,
                "publicbody_empty": True,
                "user_can_hide_web": True,
                "public_body_officials_public": False,
                "public_body_officials_email_public": False,
                "default_law": 2,
                "doc_conversion_binary": "/usr/bin/libreoffice",
                "dryrun": False,
                "read_receipt": True,
                "delivery_receipt": True,
                "dsn": True,
                "message_handlers": {
                    "email": "froide.foirequest.message_handlers.EmailMessageHandler",
                    "fax": "froide_fax.fax.FaxMessageHandler",
                },
                "delivery_reporter": "froide.foirequest.delivery.PostfixDeliveryReporter",
                "text_analyzer": "fragdenstaat_de.theme.search.get_text_analyzer",
                "search_analyzer": "fragdenstaat_de.theme.search.get_search_analyzer",
                "search_quote_analyzer": "fragdenstaat_de.theme.search.get_search_quote_analyzer",
                "dryrun_domain": "test.fragdenstaat.de",
                "allow_pseudonym": True,
                "api_activated": True,
                "search_engine_query": (
                    "http://www.google.de/search?as_q=%(query)s&as_epq=&as_oq=&as_eq=&"
                    "hl=en&lr=&cr=&as_ft=i&as_filetype=&as_qdr=all&as_occt=any&"
                    "as_dt=i&as_sitesearch=%(domain)s&as_rights=&safe=images"
                ),
                "show_public_body_employee_name": False,
                "request_throttle": [
                    (5, 5 * 60),  # X requests in X seconds
                    (6, 6 * 60 * 60),
                    (10, 24 * 60 * 60),
                    (20, 7 * 24 * 60 * 60),
                ],
                "message_throttle": [
                    (2, 5 * 60),  # X messages in X seconds
                    (6, 6 * 60 * 60),
                    (8, 24 * 60 * 60),
                ],
                "target_countries": ("DE", "CH", "AT"),
                "suspicious_asn_provider_list": env("SUSPICIOUS_ASN", "").split("|"),
                "greetings": [
                    # Important: always needs to capture name to be removed
                    rec(r"^\s*Name des Absenders\s+(.*)"),
                    rec(r"^\s*Hallo\s+(.*)"),
                    rec(r"^\s*Moin\s+(.*)"),
                    rec(r"^\s*Lieber?\s+(.*)"),
                    rec(r"^\s*Grü(?:ß|ss)\s+Gott\s+((?:Herr|Frau|Fr\.|Hr\.)\s+.*)"),
                    rec(r"^\s*Sehr ((?:Herr|Frau|Fr\.|Hr\.)\s+.*)"),
                    rec(r"^\s*Sehr (geehrte[\*:_]?[sr]?\s+(?!Damen und Herren).+)"),
                    rec(r"^\s*(?:Von|An|Cc|To|From): (.*)"),
                    rec(
                        r"^\s*Guten\s+(?:Tag|Morgen|Mittag|Abend),?[ \t\f\v]+([^\r\n]+)"
                    ),
                    rec(r"^\s*(.*) möchte die Nachricht .* zurückrufen\."),
                ],
                "custom_replacements": [
                    rec(r"[Bb][Gg]-[Nn][Rr]\.?\s*\:?\s*([a-zA-Z0-9\s/]+)"),
                    rec(r"Ihr Kennwort lautet: (.*)"),
                    rec(r"Token: ([A-Z0-9]+)"),
                    rec(r"(https://wetransfer.com/downloads/.*)"),
                    rec(r"(https://send.firefox.com/download/.*)"),
                ],
                "moderation_triggers": [
                    {
                        "name": "nonfoi",
                        "label": _("Non-FOI"),
                        "icon": "fa-ban",
                        "applied_if_actions_applied": [0],
                        "actions": [
                            ("froide.foirequest.moderation.MarkNonFOI",),
                            (
                                "froide.foirequest.moderation.SendUserEmail",
                                "foirequest/emails/non_foi",
                            ),
                        ],
                    },
                    {
                        "name": "warn_user",
                        "label": _("Give warning"),
                        "icon": "fa-minus-circle",
                        "applied_if_actions_applied": [0, 1],
                        "actions": [
                            ("froide.foirequest.moderation.Depublish",),
                            ("froide.foirequest.moderation.ApplyUserTag", "watchlist"),
                            (
                                "froide.foirequest.moderation.SendUserEmail",
                                "moderation/warn_user",
                            ),
                            (
                                "froide.foirequest.moderation.AddUserNote",
                                "{timestamp}: {moderator} send warning ({foirequest})",
                            ),
                        ],
                    },
                ],
                "closings": [
                    rec(
                        r"(?:\b([Mm]it *)?(den *)?(freun\w+|vielen|besten)? *Gr(ü|u|\?)(ß|ss|\?)(?!\s+Gott)(en?)?,?)|"
                        r"(?:\bHochachtungsvoll,?)|"
                        r"(?:\bi\. ?A\.)|"
                        r"(?:\bMfG)|"
                        r"(?:\b[iI]m Auftrag)|"
                        r"(?:\b(?:Best *regards|Kind *regards|Sincerely),?)"
                    )
                ],
                "hide_content_funcs": [
                    lambda email: email.from_[1]
                    in (
                        "noreply@dhl.com",  # Hide DHL delivery emails
                        "noreply-bscw@itzbund.de",  # Hide BSCW.bund.de auto messages
                    )
                ],
                "recipient_blocklist_regex": rec(
                    r".*\.de-mail\.de$|^z@bundesnachrichtendienst\.de|"
                    r"^pad\.donotreply@frontex\.europa\.eu|"
                    r"^noreply@.*|^empfangsbestaetigung@bahn\.de$|.*\.local$|^postmaster@.*|"
                    r"^askema\.noreply@ema\.europa\.eu$|^.*@nomail\.ec\.europa\.eu$|"
                    r"^eingangsbestaetigung@jobcenter-ge\.de$"
                ),
                "content_urls": {
                    "terms": "/nutzungsbedingungen/",
                    "privacy": "/datenschutzerklaerung/",
                    "pseudonym": "/hilfe/datenschutz-und-privatsphare/pseudonyme-nutzung/",
                    "about": "/hilfe/ueber/",
                    "help": "/hilfe/",
                    "throttled": "/hilfe/erste-anfrage/wie-viele-anfragen-kann-ich-stellen/",
                    "help_postupload_redaction": "/hilfe/plain/funktionen-der-plattform/schwaerzungen-durchfuehren/",
                    "help_attachments_management": "/hilfe/plain/funktionen-der-plattform/anhange-verwalten/",
                },
                "mobile_app_content_url": "/app/scanner/postupload/message/{}/",
                "bounce_enabled": True,
                "bounce_max_age": 60 * 60 * 24 * 14,  # 14 days
                "bounce_format": "bounce+{token}@fragdenstaat.de",
                "unsubscribe_enabled": True,
                "unsubscribe_format": "unsub+{token}@fragdenstaat.de",
                "auto_reply_subject_regex": rec(
                    r"^(Auto-?Reply|Out of office|Out of the office|Abwesenheitsnotiz|"
                    r"Automatische Antwort|automatische Empfangsbestätigung)"
                ),
                "auto_reply_email_regex": rec("^auto(reply|responder|antwort)@"),
                "non_meaningful_subject_regex": [
                    r"^(ifg[- ])?anfrage$",
                    r"^dokumente?$",
                    r"^infos?$",
                    r"^information(en)?$",
                    r"^e-?mails?$",
                    r"^kommunikation$",
                ],
                "address_regex": r"\d{4,5}",
            }
        )
        return config

    FROIDE_FOOD_CONFIG = {
        "api_key_google": os.environ.get("GOOGLE_PLACES_API_KEY"),
        "api_key_geocode_here": os.environ.get("HERE_GEOCODE_API_KEY"),
        "api_key_geocode_mapbox": os.environ.get("MAPBOX_API_KEY"),
        "api_key_yelp": os.environ.get("YELP_API_KEY", ""),
        "api_key_foursquare": os.environ.get("FOURSQUARE_API_KEY"),
    }
    GOVPLAN_NAME = "Koalitionstracker"
    AMENITY_CATEGORY_FUNC = None
    AMENITY_TOPICS = {
        "public": (
            ("building", "sports_centre"),
            ("leisure", "sports_centre"),
            ("building", "public"),
            ("building", "civic"),
            ("building", "school"),
            ("building", "government"),
            ("amenity", "townhall"),
            ("amenity", "library"),
            ("amenity", "police"),
            ("amenity", "school"),
            ("amenity", "community_centre"),
            ("amenity", "archive"),
            ("amenity", "courthouse"),
            ("amenity", "hospital"),
            ("amenity", "clinic"),
            ("amenity", "public_building"),
            ("office", "government"),
            ("office", "administrative"),
            ("government", "*"),
        ),
        "food": (
            ("amenity", "bar"),
            ("amenity", "biergarten"),
            ("amenity", "cafe"),
            ("amenity", "fast_food"),
            ("amenity", "pub"),
            ("amenity", "restaurant"),
            ("amenity", "casino"),
            ("amenity", "cinema"),
            ("amenity", "nightclub"),
            ("amenity", "food_court"),
            ("amenity", "ice_cream"),
            ("amenity", "fuel"),
            ("shop", "alcohol"),
            ("shop", "bakery"),
            ("shop", "beverages"),
            ("shop", "butcher"),
            ("shop", "cheese"),
            ("shop", "chocolate"),
            ("shop", "coffee"),
            ("shop", "confectionery"),
            ("shop", "convenience"),
            ("shop", "deli"),
            ("shop", "dairy"),
            ("shop", "farm"),
            ("shop", "frozen_food"),
            ("shop", "greengrocer"),
            ("shop", "health_food"),
            ("shop", "ice_cream"),
            ("shop", "organic"),
            ("shop", "pasta"),
            ("shop", "pastry"),
            ("shop", "seafood"),
            ("shop", "spices"),
            ("shop", "tea"),
            ("shop", "wine"),
            ("shop", "water"),
            ("shop", "department_store"),
            ("shop", "general"),
            ("shop", "kiosk"),
            ("shop", "supermarket"),
            ("shop", "wholesale"),
            ("tourism", "hostel"),
            ("tourism", "hotel"),
            ("tourism", "theme_park"),
        ),
    }

    FDS_OGIMAGE_URL = "https://ogimage.frag-den-staat.de/api/{hash}?path={path}"
    APP_SITE_URL = "https://app.fragdenstaat.de"

    TELNYX_APP_ID = os.environ.get("TELNYX_APP_ID", "")
    TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY", "")
    TELNYX_PUBLIC_KEY = os.environ.get("TELNYX_PUBLIC_KEY", "")
    TELNYX_FROM_NUMBER = os.environ.get("TELNYX_FROM_NUMBER", "")

    SLACK_DEFAULT_CHANNEL = os.environ.get(
        "SLACK_DEFAULT_CHANNEL", "fragdenstaat-notifications"
    )
    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
    MATOMO_API_URL = os.environ.get("MATOMO_API_URL", "")
    MATOMO_GOAL_ID = os.environ.get("MATOMO_GOAL_ID", "7")

    SENTRY_JS_URL = ""
    MATOMO_SITE_ID = ""

    FRONTEX_CAPTCHA_MODEL_PATH = os.environ.get("FRONTEX_CAPTCHA_MODEL_PATH", None)

    DJANGOCMS_ICON_SETS = [
        ("fontawesome4", "fa", "Font Awesome 4", "4.7.0"),
    ]

    PAPERLESS_API_URL = os.environ.get("PAPERLESS_API_URL", "")
    PAPERLESS_API_TOKEN = os.environ.get("PAPERLESS_API_TOKEN", "")
    PAPERLESS_UPLOADED_TYPE = os.environ.get(
        "PAPERLESS_UPLOADED_TYPE", ""
    )  # Tag for successfully uploaded documents
    PAPERLESS_REQUEST_FIELD = os.environ.get(
        "PAPERLESS_REQUEST_FIELD", ""
    )  # custom_field id for foirequest reference

    LEAFLET_CONFIG = {
        "TILES": [
            (
                "Carto",
                "//cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
                '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attribution">CARTO</a>',
            )
        ]
    }

    FROIDE_EVIDENCECOLLECTION_NOCODB_IMPORT_CONFIG = values.DictValue(
        {
            "api_url": os.environ.get("FROIDE_EVIDENCECOLLECTION_NOCODB_API_URL", ""),
            "api_token": os.environ.get(
                "FROIDE_EVIDENCECOLLECTION_NOCODB_API_TOKEN", ""
            ),
            "tables": {
                "PersonOrOrganization": os.environ.get(
                    "FROIDE_EVIDENCECOLLECTION_NOCODB_PERSON_TABLE"
                ),
                "Source": os.environ.get(
                    "FROIDE_EVIDENCECOLLECTION_NOCODB_SOURCE_TABLE"
                ),
                "Evidence": os.environ.get(
                    "FROIDE_EVIDENCECOLLECTION_NOCODB_EVIDENCE_TABLE"
                ),
                "Group": os.environ.get("FROIDE_EVIDENCECOLLECTION_NOCODB_GROUP_TABLE"),
            },
            "field_map": {
                "PersonOrOrganization": {
                    "external_id": "id",
                    "name": "Name/Bezeichnung",
                    "regions": "Region(en)",
                    "is_active": "Aktiv",
                },
                "Source": {
                    "external_id": "id",
                    "reference_value": "Referenzwert",
                    "persons_or_organizations": "_nc_m2m_Quellen und Nac_Personen und Ors",
                    "url": "Quelle",
                    "attribution_bases": "Mitgliedzurechnung",
                    "file_reference": "Aktenzeichen",
                    "document_number": "Dokumentennummer",
                    "is_on_record": "Aktenkundig?",
                    "recorded_by": "_nc_m2m_Quellen und Nac_publicbodies",
                },
                "Evidence": {
                    "external_id": "id",
                    "description": "Zusammenfassung",
                    "date": "Datum der Aussage/Aktion",
                    "type": "Art des Belegs",
                    "categories": "Zuordnung zu FDGO-Merkmalen",
                    "spread_level": "Verbreitungsgrad",
                    "distribution_channels": "Verbreitungswege",
                    "sources": "_nc_m2m_Quellen und Nac_Belege und Ausses",
                    "is_verified": "Geprüft?",
                    "requires_additional_review": "Zusätzliche Prüfung notwendig?",
                },
                "Group": {
                    "external_id": "id",
                    "name": "Name",
                    "members": "_nc_m2m_Personen und Or_Gruppen und Orgs",
                },
            },
            "relations": {
                "PersonOrOrganization": {
                    "regions": {
                        "type": "m2m",
                        "model": "georegion.GeoRegion",
                        "lookup_field": "id",
                    }
                },
                "Source": {
                    "persons_or_organizations": {
                        "type": "m2m",
                        "model": "froide_evidencecollection.PersonOrOrganization",
                        "lookup_field": "external_id",
                    },
                    "attribution_bases": {
                        "type": "m2m",
                        "model": "froide_evidencecollection.AttributionBasis",
                        "lookup_field": "name",
                        "create_if_missing": True,
                    },
                    "recorded_by": {
                        "type": "fk",
                        "model": "publicbody.PublicBody",
                        "lookup_field": "id",
                    },
                },
                "Evidence": {
                    "type": {
                        "type": "fk",
                        "model": "froide_evidencecollection.EvidenceType",
                        "lookup_field": "name",
                        "create_if_missing": True,
                    },
                    "spread_level": {
                        "type": "fk",
                        "model": "froide_evidencecollection.SpreadLevel",
                        "lookup_field": "name",
                        "create_if_missing": True,
                    },
                    "categories": {
                        "type": "m2m",
                        "model": "froide_evidencecollection.EvidenceCategory",
                        "lookup_field": "name",
                        "create_if_missing": True,
                    },
                    "distribution_channels": {
                        "type": "m2m",
                        "model": "froide_evidencecollection.DistributionChannel",
                        "lookup_field": "name",
                        "create_if_missing": True,
                    },
                    "sources": {
                        "type": "m2m",
                        "model": "froide_evidencecollection.Source",
                        "lookup_field": "external_id",
                    },
                },
                "Group": {
                    "members": {
                        "type": "m2m",
                        "model": "froide_evidencecollection.PersonOrOrganization",
                        "lookup_field": "external_id",
                    }
                },
            },
            "institution_role_map": {
                "AfD-Bundespartei": "Bundespartei Funktion(en)",
                "AfD-Länderparteien": "Landesparteien Funktion(en)",
                "Funktionär(in)": "Funktionäre Funktion(en)",
                "Umfeld": "Umfeld Funktion(en)",
            },
            "selectable_regions": {
                # Germany and its federal states
                "ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
            },
            "special_regions": ["Ausland"],
            "null_label": "Keine Angabe",
        }
    )

    DATASHOW_STORAGE_BACKEND = "overwrite"

    COOKIE_CONSENT_LOG_ENABLED = False
    COOKIE_CONSENT_SECURE = False
