from .production import FragDenStaat

class Docker(FragDenStaat):
    FRONTEND_DEBUG=True
    PAYMENT_VARIANTS = {
        "creditcard": (
            "froide_payment.provider.StripeIntentProvider",
            {
                "public_key": env("STRIPE_PUBLIC_KEY"),
                "secret_key": env("STRIPE_PRIVATE_KEY"),
                "signing_secret": env("STRIPE_WEBHOOK_CC_SIGNING_KEY"),
            },
        ),
        "sepa": (
            "froide_payment.provider.StripeSEPAProvider",
            {
                "public_key": env("STRIPE_PUBLIC_KEY"),
                "secret_key": env("STRIPE_PRIVATE_KEY"),
                "signing_secret": env("STRIPE_WEBHOOK_SEPA_SIGNING_KEY"),
            },
        ),
        "paypal": (
            "froide_payment.provider.PaypalProvider",
            {
                "client_id": env("PAYPAL_CLIENT_ID"),
                "secret": env("PAYPAL_CLIENT_SECRET"),
                "endpoint": env("PAYPAL_API_URL"),
                "capture": True,
                "webhook_id": env("PAYPAL_WEBHOOK_ID"),
            },
        ),
        "sofort": (
            "froide_payment.provider.StripeSofortProvider",
            {
                # Test API keys
                "public_key": env("STRIPE_PUBLIC_KEY"),
                "secret_key": env("STRIPE_PRIVATE_KEY"),
                # separate Webhook signing secret
                "signing_secret": env("STRIPE_WEBHOOK_SOFORT_SIGNING_KEY"),
            },
        ),
        "lastschrift": ("froide_payment.provider.LastschriftProvider", {}),
        "banktransfer": ("froide_payment.provider.BanktransferProvider", {}),
    }

    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = "/tmp/app-messages"
    FOI_MAIL_SERVER_HOST = env("FOI_MAIL_SERVER_HOST", "localhost")
