import os
import re
from datetime import timedelta
from pathlib import Path

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
            ["fragdenstaat_de.theme"]
            + installed.default
            + [
                "django.contrib.postgres",
                "cms",
                "menus",
                "sekizai",
                "easy_thumbnails",
                "easy_thumbnails.optimize",
                "filer",
                "mptt",
                "logentry_admin",
                "localflavor",
                "fragdenstaat_de.fds_blog",
                "adminsortable2",
                # Customisations
                "fragdenstaat_de.fds_newsletter",
                "fragdenstaat_de.fds_cms.apps.FdsCmsConfig",
                "fragdenstaat_de.fds_donation.apps.FdsDonationConfig",
                "fragdenstaat_de.fds_mailing.apps.FdsMailingConfig",
                "fragdenstaat_de.fds_ogimage.apps.FdsOgImageConfig",
                "fragdenstaat_de.fds_fximport.apps.FdsFxImportConfig",
                # Additional CMS plugins
                "djangocms_text_ckeditor",
                "djangocms_picture",
                "djangocms_video",
                "djangocms_icon",
                "djangocms_frontend",
                "djangocms_frontend.contrib.accordion",
                "djangocms_frontend.contrib.alert",
                "djangocms_frontend.contrib.badge",
                "djangocms_frontend.contrib.card",
                "djangocms_frontend.contrib.carousel",
                "djangocms_frontend.contrib.collapse",
                "djangocms_frontend.contrib.content",
                "djangocms_frontend.contrib.grid",
                "djangocms_frontend.contrib.image",
                "djangocms_frontend.contrib.jumbotron",
                "djangocms_frontend.contrib.link",
                "djangocms_frontend.contrib.listgroup",
                "djangocms_frontend.contrib.media",
                "djangocms_frontend.contrib.tabs",
                "djangocms_frontend.contrib.utilities",
                # Additional CMS plugins
                "sortabletable",
                "contractor",
                "djcelery_email",
                "django.contrib.redirects",
                "django_prices",
                "froide_campaign.apps.FroideCampaignConfig",
                "froide_legalaction.apps.FroideLegalActionConfig",
                "froide_payment.apps.FroidePaymentConfig",
                "froide_crowdfunding.apps.FroideCrowdfundingConfig",
                "froide_food.apps.FroideFoodConfig",
                "django_amenities.apps.AmenitiesConfig",
                "froide_fax.apps.FroideFaxConfig",
                "froide_exam",
                "froide_govplan.apps.FroideGovPlanConfig",
                "legal_advice_builder.apps.LegalAdviceBuilderConfig",
                "fcdocs_annotate.annotation.apps.AnnotationConfig",
                "tinymce",
            ]
        )
        return installed.default

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
    NEWSLETTER_RICHTEXT_WIDGET = "djangocms_text_ckeditor.widgets.TextEditorWidget"
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

    # Campaign

    CAMPAIGN_PROVIDERS = [
        ("", "froide_campaign.providers.base.BaseProvider"),
        ("amenity", "froide_campaign.providers.amenity.AmenityProvider"),
        ("publicbody", "froide_campaign.providers.publicbody.PublicBodyProvider"),
        (
            "amenity_local",
            "froide_campaign.providers.amenity_local.AmenityLocalProvider",
        ),
    ]

    # BLOG

    ARTICLE_CONTENT_TEMPLATES = [
        ("fds_blog/content/_article_no_image.html", _("No image in article"))
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
    CMS_RAW_ID_USERS = 50

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

    CMS_TOOLBAR_ANONYMOUS_ON = False
    CMS_TEMPLATES = [
        ("cms/home.html", "Homepage template"),
        ("cms/page.html", "Page template"),
        ("cms/page_headerless.html", "Page without header"),
        ("cms/page_reduced.html", "Page reduced"),
        ("cms/page_breadcrumb.html", "Page with breadcrumbs"),
        ("cms/blog_base.html", "Blog base template"),
        ("cms/help_base.html", "Help base template"),
        ("froide_govplan/base.html", "Govplan base template"),
    ]
    DONATION_LOGIC_PLUGINS = [
        "IsDonorPlugin",
        "IsNotDonorPlugin",
        "IsRecurringDonorPlugin",
        "IsNotRecurringDonorPlugin",
        "IsRecentDonor",
        "IsNotRecentDonor",
        "ConcactAllowedDonor",
        "ConcactNotAllowedDonor",
    ]
    CMS_PLACEHOLDER_CONF = {
        "email_body": {
            "plugins": [
                "TextPlugin",
                "EmailActionPlugin",
                "EmailSectionPlugin",
                "EmailStoryPlugin",
                "EmailBodyPlugin",
                "EmailHeaderPlugin",
                "PicturePlugin",
            ]
            + DONATION_LOGIC_PLUGINS,
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

    # Set to False until this is fixed
    # https://github.com/divio/django-cms/issues/5725
    CMS_PAGE_CACHE = False

    TEXT_ADDITIONAL_TAGS = (
        "iframe",
        "embed",
    )
    TEXT_ADDITIONAL_ATTRIBUTES = (
        "scrolling",
        "frameborder",
        "webkitallowfullscreen",
        "mozallowfullscreen",
        "allowfullscreen",
        "sandbox",
        "style",
    )
    TEXT_ADDITIONAL_PROTOCOLS = ("bank",)

    CKEDITOR_SETTINGS = {
        "language": "{{ language }}",
        "skin": "moono-lisa",
        "toolbar": "CMS",
        "toolbar_CMS": [
            ["Undo", "Redo"],
            ["cmsplugins", "-"],
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
                "Blockquote",
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
        "extraPlugins": "autocorrect",
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
    THUMBNAIL_PRESERVE_EXTENSIONS = ("png",)

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
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
        "default": {"hosts": "localhost:9200"},
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
    DONATION_ARCHIVE_INBOX = "spendenbescheinigungen@okfn.de"

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
            dict(
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
                    "email": "froide.foirequest.message_handlers.EmailMessageHandler",
                    "fax": "froide_fax.fax.FaxMessageHandler",
                },
                delivery_reporter="froide.foirequest.delivery.PostfixDeliveryReporter",
                text_analyzer="fragdenstaat_de.theme.search.get_text_analyzer",
                search_analyzer="fragdenstaat_de.theme.search.get_search_analyzer",
                search_quote_analyzer="fragdenstaat_de.theme.search.get_search_quote_analyzer",
                dryrun_domain="test.fragdenstaat.de",
                allow_pseudonym=True,
                api_activated=True,
                search_engine_query=(
                    "http://www.google.de/search?as_q=%(query)s&as_epq=&as_oq=&as_eq=&"
                    "hl=en&lr=&cr=&as_ft=i&as_filetype=&as_qdr=all&as_occt=any&"
                    "as_dt=i&as_sitesearch=%(domain)s&as_rights=&safe=images"
                ),
                show_public_body_employee_name=False,
                request_throttle=[
                    (5, 5 * 60),  # X requests in X seconds
                    (6, 6 * 60 * 60),
                    (10, 24 * 60 * 60),
                    (20, 7 * 24 * 60 * 60),
                ],
                message_throttle=[
                    (2, 5 * 60),  # X messages in X seconds
                    (6, 6 * 60 * 60),
                    (8, 24 * 60 * 60),
                ],
                target_countries=("DE", "CH", "AT"),
                greetings=[
                    # Important: always needs to capture name to be removed
                    rec(r"^\s*Name des Absenders\s+(.*)"),
                    rec(r"^\s*Hallo\s+(.*)"),
                    rec(r"^\s*Lieber?\s+(.*)"),
                    rec(r"^\s*Grü(?:ß|ss)\s+Gott\s+((?:Herr|Frau|Fr\.|Hr\.)\s+.*)"),
                    rec(r"^\s*Sehr ((?:Herr|Frau|Fr\.|Hr\.)\s+.*)"),
                    rec(r"^\s*Sehr (geehrte[\*:_]?[sr]?\s+(?!Damen und Herren).+)"),
                    rec(r"^\s*(?:Von|An|Cc|To|From): (.*)"),
                ],
                custom_replacements=[
                    rec(r"[Bb][Gg]-[Nn][Rr]\.?\s*\:?\s*([a-zA-Z0-9\s/]+)"),
                    rec(r"Ihr Kennwort lautet: (.*)"),
                    rec(r"Token: ([A-Z0-9]+)"),
                    rec(r"(https://wetransfer.com/downloads/.*)"),
                    rec(r"(https://send.firefox.com/download/.*)"),
                ],
                moderation_triggers=[
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
                closings=[
                    rec(
                        r"\b([Mm]it *)?(den *)?(freun\w+|vielen|besten)? "
                        r"*Gr(ü|u|\?)(ß|ss|\?)(?!\s+Gott)(en?)?,?"
                    ),
                    rec(r"\bHochachtungsvoll,?"),
                    rec(r"\bi\. ?A\."),
                    rec(r"\bMfG"),
                    rec(r"\b[iI]m Auftrag"),
                    rec(r"\b(?:Best *regards|Kind *regards|Sincerely),?"),
                ],
                hide_content_funcs=[
                    lambda email: email.from_[1]
                    in (
                        "noreply@dhl.com",  # Hide DHL delivery emails
                        "noreply-bscw@itzbund.de",  # Hide BSCW.bund.de auto messages
                    )
                ],
                recipient_blocklist_regex=rec(
                    r".*\.de-mail\.de$|^z@bundesnachrichtendienst.de|"
                    r"^pad.donotreply@frontex.europa.eu|"
                    r"^noreply@.*|^empfangsbestaetigung@bahn.de$|.*\.local$|^postmaster@.*|"
                    r"^askema.noreply@ema.europa.eu$"
                ),
                content_urls={
                    "terms": "/nutzungsbedingungen/",
                    "privacy": "/datenschutzerklaerung/",
                    "pseudonym": "/hilfe/datenschutz-und-privatsphare/pseudonyme-nutzung/",
                    "about": "/hilfe/ueber/",
                    "help": "/hilfe/",
                },
                bounce_enabled=True,
                bounce_max_age=60 * 60 * 24 * 14,  # 14 days
                bounce_format="bounce+{token}@fragdenstaat.de",
                unsubscribe_enabled=True,
                unsubscribe_format="unsub+{token}@fragdenstaat.de",
                auto_reply_subject_regex=rec(
                    r"^(Auto-?Reply|Out of office|Out of the office|Abwesenheitsnotiz|"
                    r"Automatische Antwort|automatische Empfangsbestätigung)"
                ),
                auto_reply_email_regex=rec("^auto(reply|responder|antwort)@"),
                non_meaningful_subject_regex=[
                    r"^(ifg[- ])?anfrage$",
                    r"^dokumente?$",
                    r"^infos?$",
                    r"^information(en)?$",
                    r"^e-?mails?$",
                    r"^kommunikation$",
                ],
            )
        )
        return config

    FROIDE_FOOD_CONFIG = {
        "api_key_google": os.environ.get("GOOGLE_PLACES_API_KEY"),
        "api_key_geocode_here": os.environ.get("HERE_GEOCODE_API_KEY"),
        "api_key_geocode_mapbox": os.environ.get("MAPBOX_API_KEY"),
        "api_key_yelp": os.environ.get("YELP_API_KEY", ""),
        "api_key_foursquare": os.environ.get("FOURSQUARE_API_KEY"),
    }
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

    TELNYX_APP_ID = os.environ.get("TELNYX_APP_ID", "")
    TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY", "")
    TELNYX_PUBLIC_KEY = os.environ.get("TELNYX_PUBLIC_KEY", "")
    TELNYX_FROM_NUMBER = os.environ.get("TELNYX_FROM_NUMBER", "")

    SLACK_DEFAULT_CHANNEL = os.environ.get(
        "SLACK_DEFAULT_CHANNEL", "fragdenstaat-alerts"
    )
    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

    SENTRY_JS_URL = ""

    FRONTEX_CAPTCHA_MODEL_PATH = os.environ.get("FRONTEX_CAPTCHA_MODEL_PATH", None)
