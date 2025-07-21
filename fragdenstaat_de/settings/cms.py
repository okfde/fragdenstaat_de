import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _

from configurations import Configuration, importer, values

import froide

importer.install(check_options=True)


class CMSSettingsMixin:
    CMS_PERMISSION = True
    CMS_RAW_ID_USERS = True
    CMS_CONFIRM_VERSION4 = True
    CMS_MIGRATION_USER_ID = 1

    CMS_CORE_APPS = [
        "fragdenstaat_de.fds_cms.apps.FdsCmsNoConfig",
        "djangocms_versioning",
        "cms",
        "djangocms_alias",
        "menus",
        "sekizai",
        # "djangocms_transfer",
        # easy thumbnails comes from froide
        "filer",
    ]
    CMS_EXTRA_APPS = [
        # Additional CMS plugins
        "djangocms_text",
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
    ]

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
        },
        "embed": {"type", "src", "width", "height"},
        "summary": {"class"},
        "details": {"class", "open"},
        "*": {"style"},
    }
    TEXT_EDITOR = "fragdenstaat_de.theme.editor.ckeditor4"

    TEXT_EDITOR_SETTINGS = {
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
        "stylesSet": "default:/static/js/cms/ckeditor.wysiwyg.js",
        "contentsCss": "/static/css/main.css",
    }

    DJANGOCMS_PICTURE_TEMPLATES = [("hero", _("Hero")), ("email", _("Email"))]

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


class CMSSiteBase(CMSSettingsMixin, Configuration):
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DEBUG = True
    ROOT_URLCONF = "fragdenstaat_de.theme.cms_urls"

    BASE_DIR = PROJECT_ROOT.parent
    FRONTEND_BUILD_DIR = BASE_DIR / "build"
    FRONTEND_SERVER_URL = "http://localhost:5173/static/"

    LANGUAGE_CODE = "de"
    LANGUAGES = (
        ("en", _("English")),
        ("de", _("German")),
    )
    SECRET_KEY = "change-me"
    SECRET_URLS = {}

    @property
    def INSTALLED_APPS(self):
        return (
            [
                "django.contrib.auth",
                "django.contrib.contenttypes",
                "django.contrib.sessions",
                "django.contrib.sites",
                "django.contrib.messages",
                "django.contrib.staticfiles",
                "django.contrib.sitemaps",
                "django.contrib.humanize",
                "django.contrib.redirects",
                "django.contrib.admin.apps.SimpleAdminConfig",
            ]
            + [
                "froide.account.apps.AccountNoConfig",
                "froide.team.apps.TeamNoConfig",
                "froide.accesstoken.apps.AccessTokenNoConfig",
                "froide.helper",
            ]
            + self.CMS_CORE_APPS
            + ["easy_thumbnails", "treebeard"]
            + self.CMS_EXTRA_APPS
            + [
                "datashow",
                "filingcabinet",
                "froide.document.apps.DocumentNoConfig",
                "froide.georegion",
                "froide.publicbody.apps.PublicBodyNoConfig",
                "froide.campaign",
                "froide.foirequest.apps.FoiRequestNoConfig",
            ]
            + ["oauth2_provider", "mfa", "taggit", "cookie_consent"]
        )

    AUTH_USER_MODEL = values.Value("account.User")
    FILINGCABINET_DOCUMENT_MODEL = "document.Document"
    FILINGCABINET_DOCUMENTCOLLECTION_MODEL = "document.DocumentCollection"
    FILINGCABINET_MEDIA_PUBLIC_PREFIX = "docs"
    FILINGCABINET_MEDIA_PRIVATE_PREFIX = "docs-private"

    STATIC_URL = values.Value("/static/")
    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [
                PROJECT_ROOT / "templates/cmssites",
                PROJECT_ROOT / "templates",
                Path(froide.__file__).parent / "templates",
            ],
            "OPTIONS": {
                "debug": values.BooleanValue(DEBUG),
                "loaders": [
                    "django.template.loaders.filesystem.Loader",
                    "django.template.loaders.app_directories.Loader",
                ],
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.i18n",
                    "django.template.context_processors.media",
                    "django.template.context_processors.static",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                    "sekizai.context_processors.sekizai",
                    "cms.context_processors.cms_settings",
                    "fragdenstaat_de.theme.context_processors.theme_settings",
                    "froide.helper.context_processors.site_settings",
                ],
            },
        }
    ]

    MIDDLEWARE = [
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.locale.LocaleMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "cms.middleware.user.CurrentUserMiddleware",
        "cms.middleware.page.CurrentPageMiddleware",
        "cms.middleware.toolbar.ToolbarMiddleware",
        "fragdenstaat_de.theme.redirects.PathRedirectFallbackMiddleware",
    ]

    @property
    def FILER_STORAGES(self):
        MEDIA_ROOT = self.MEDIA_ROOT
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
        }

    GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH")
    GEOS_LIBRARY_PATH = os.environ.get("GEOS_LIBRARY_PATH")

    FDS_THUMBNAIL_ENABLE_AVIF = False

    # FIXME: Make these dummy values unnecessary
    FROIDE_CONFIG = {
        "bounce_format": "",
        "unsubscribe_format": "",
        "bounce_max_age": 0,
        "bounce_enabled": False,
        "max_attachment_size": 0,
    }
    MIN_PASSWORD_LENGTH = 9

    DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

    CACHES = {
        "default": {
            # 'LOCATION': 'unique-snowflake',
            # "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }

    @property
    def ELASTICSEARCH_INDEX_PREFIX(self):
        return self.SITE_KEY

    @property
    def MFA_DOMAIN(self):
        return self.SITE_URL.rsplit("/", 1)[1]

    @property
    def MFA_SITE_TITLE(self):
        return self.SITE_NAME

    @property
    def LOCALE_PATHS(self):
        locales = list(super().LOCALE_PATHS)
        return [
            self.PROJECT_ROOT / "locale",
        ] + locales


class GegenrechtsschutzMixin:
    SITE_ID = 2
    SITE_KEY = "grs"
    SITE_URL = "https://gegenrechtsschutz.de"
    SITE_NAME = "Gegenrechtsschutz"
    SITE_EMAIL = "info@gegenrechtsschutz.de"
    SITE_LOGO = ""
    MATOMO_SITE_ID = "57"
    SENTRY_JS_URL = ""

    CMS_TEMPLATES = [
        ("cmssites/cmssite/gegenrechtsschutz.html", "Gegenrechtsschutz Template"),
    ]
