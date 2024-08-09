import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from cms.models.pluginmodel import CMSPlugin
from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase

from froide.helper.email_sending import mail_registry

from . import subscribed, unsubscribed

logger = logging.getLogger(__name__)

REFERENCE_PREFIX = "newsletter-"


subscriber_confirm_email = mail_registry.register(
    "fds_newsletter/email/subscriber_confirm",
    ("name", "newsletter", "action_url", "unsubscribe_url"),
)

subscriber_batch_confirm_email = mail_registry.register(
    "fds_newsletter/email/subscriber_batch_confirm",
    ("name", "newsletter", "action_url", "unsubscribe_url"),
)


subscriber_already_email = mail_registry.register(
    "fds_newsletter/email/subscriber_already", ("name", "newsletter", "unsubscribe_url")
)


def get_email_context(subscriber):
    site = Site.objects.get_current()
    context = {
        "subscriber": subscriber,
        "newsletter": subscriber.newsletter,
        "site": site,
        "site_name": settings.SITE_NAME,
        "site_url": settings.SITE_URL,
        "domain": site.domain,
        "unsubscribe_url": subscriber.get_unsubscribe_url(),
        "STATIC_URL": settings.STATIC_URL,
        "MEDIA_URL": settings.MEDIA_URL,
        "unsubscribe_reference": "{prefix}{pk}".format(
            prefix=REFERENCE_PREFIX, pk=subscriber.id
        ),
    }

    if subscriber.user:
        user = subscriber.user
        context.update(
            {
                "user": user,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "name": user.get_full_name(),
                "login_url": user.get_autologin_url("/"),
            }
        )
    else:
        context.update(
            {
                "name": subscriber.get_name(),
            }
        )
    return context


class NewsletterManager(models.Manager):
    def get_visible(self):
        return self.filter(visible=True)


class Newsletter(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("newsletter title"))
    slug = models.SlugField(db_index=True, unique=True)
    url = models.URLField(blank=True)

    description = models.TextField(blank=True)

    sender_email = models.EmailField(
        verbose_name=_("e-mail"), help_text=_("Sender e-mail")
    )
    sender_name = models.CharField(
        max_length=200, verbose_name=_("sender"), help_text=_("Sender name")
    )

    visible = models.BooleanField(default=True, verbose_name=_("visible"))

    objects = NewsletterManager()

    class Meta:
        verbose_name = _("newsletter")
        verbose_name_plural = _("newsletters")

    def __str__(self):
        return self.title


class SubscriberTag(TagBase):
    class Meta:
        verbose_name = _("Subscriber Tag")
        verbose_name_plural = _("Subscriber Tags")


class TaggedSubscriber(TaggedItemBase):
    tag = models.ForeignKey(
        SubscriberTag, related_name="subscribers", on_delete=models.CASCADE
    )
    content_object = models.ForeignKey("Subscriber", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Tagged Subscriber")
        verbose_name_plural = _("Tagged Subscribers")


def make_activation_code():
    return get_random_string(length=40)


class Subscriber(models.Model):
    newsletter = models.ForeignKey(
        Newsletter,
        verbose_name=_("newsletter"),
        on_delete=models.CASCADE,
        related_name="subscribers",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        verbose_name=_("user"),
        on_delete=models.CASCADE,
        related_name="+",
    )

    name = models.CharField(_("name"), max_length=100, blank=True)
    email = models.EmailField(
        verbose_name=_("e-mail"), db_index=True, blank=True, null=True
    )
    send_html = models.BooleanField(default=True)

    created = models.DateTimeField(editable=False, default=timezone.now)

    last_activation_sent = models.DateTimeField(null=True, blank=True)

    activation_code = models.CharField(
        _("activation code"), max_length=40, default=make_activation_code
    )

    subscribed = models.DateTimeField(_("subscribe date"), null=True, blank=True)

    unsubscribed = models.DateTimeField(
        verbose_name=_("unsubscribe date"), null=True, blank=True
    )
    unsubscribe_method = models.CharField(max_length=255, blank=True)
    email_hash = models.CharField(max_length=64, blank=True)

    reference = models.CharField(max_length=255, blank=True)
    keyword = models.CharField(max_length=255, blank=True)

    tags = TaggableManager(through=TaggedSubscriber, blank=True)

    class Meta:
        verbose_name = _("newsletter subscriber")
        verbose_name_plural = _("newsletter subscribers")
        ordering = ("-created",)
        constraints = [
            models.UniqueConstraint(
                fields=["newsletter", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_user_newsletter",
            ),
            models.UniqueConstraint(
                fields=["newsletter", "email"],
                condition=models.Q(email__isnull=False),
                name="unique_email_newsletter",
            ),
            models.CheckConstraint(
                check=models.Q(user__isnull=True, email__isnull=False)
                | models.Q(user__isnull=False, email__isnull=True)
                | models.Q(
                    user__isnull=True, email__isnull=True, unsubscribed__isnull=False
                ),
                name="newsletter_subscription_user_email",
            ),
            models.CheckConstraint(
                check=~models.Q(subscribed__isnull=False, unsubscribed__isnull=False),
                name="newsletter_subscription_state",
            ),
        ]

    def __str__(self):
        return "{} <{}> ({})".format(self.id, self.get_email(), self.newsletter)

    def clean(self):
        nl_qs = Subscriber.objects.filter(newsletter=self.newsletter)
        if self.email and nl_qs.filter(user__email=self.email).exists():
            raise ValidationError(_("User with that email already present."))
        elif self.user and nl_qs.filter(email=self.user.email).exists():
            raise ValidationError(_("Email for this user already present."))

    def get_name(self):
        if self.user:
            return self.user.get_full_name()
        return self.name

    def get_email(self):
        if self.user:
            return self.user.email
        return self.email

    def is_reference(self):
        return {self.reference: True}

    def get_email_context(self):
        return get_email_context(self)

    def send_mail_intent(self, intent):
        context = self.get_email_context()
        return intent.send(
            email=self.email, user=self.user, context=context, priority=False
        )

    def send_activation_email(self, batch=False):
        context = self.get_email_context()
        context["action_url"] = self.get_subscribe_url()
        if batch:
            email_intent = subscriber_batch_confirm_email
        else:
            email_intent = subscriber_confirm_email

        email_intent.send(
            email=self.email,
            user=self.user,
            context=context,
            ignore_active=True,
            priority=True,
        )
        self.last_activation_sent = timezone.now()
        self.save()

    def send_already_email(self):
        context = self.get_email_context()
        subscriber_already_email.send(
            email=self.email,
            user=self.user,
            context=context,
            ignore_active=True,
            priority=True,
        )
        self.last_activation_sent = timezone.now()
        self.save()

    def get_subscribe_url(self):
        return settings.SITE_URL + reverse(
            "newsletter_confirm_subscribe",
            kwargs={
                "newsletter_slug": self.newsletter.slug,
                "pk": self.pk,
                "activation_code": self.activation_code,
            },
        )

    def get_unsubscribe_url(self):
        if self.user:
            return (
                self.user.get_autologin_url(reverse("account-settings")) + "#newsletter"
            )
        return settings.SITE_URL + reverse(
            "newsletter_confirm_unsubscribe",
            kwargs={
                "newsletter_slug": self.newsletter.slug,
                "pk": self.pk,
                "activation_code": self.activation_code,
            },
        )

    def find_user(self):
        User = get_user_model()
        try:
            return User.objects.get(email=self.email, is_active=True)
        except User.DoesNotExist:
            return

    def find_user_subscriber(self, user):
        try:
            return Subscriber.objects.get(newsletter=self.newsletter, user=user)
        except Subscriber.DoesNotExist:
            pass

    def subscribe(self, reference="", keyword="", batch=False):
        if self.email:
            # Check for existing user / subscriber
            user = self.find_user()
            if user:
                user_subscriber = self.find_user_subscriber(user)
                if user_subscriber:
                    # remove subscriber in favour of found one
                    self.delete()
                    user_subscriber.subscribe()
                    return user_subscriber
                else:
                    # Switch subscriber to user
                    self.email = None
                    self.user = user
                    if self.subscribed:
                        self.save()

        if self.subscribed:
            return self

        self.unsubscribed = None
        self.subscribed = timezone.now()
        if reference:
            self.reference = reference
        if keyword:
            self.keyword = keyword

        self.save()

        if self.user:
            # Delete alternate email subscribers
            Subscriber.objects.filter(
                newsletter=self.newsletter, email=self.user.email.lower()
            ).delete()
        subscribed.send(sender=self, batch=batch)
        return self

    def unsubscribe(self, method=""):
        if self.unsubscribed:
            return
        self.subscribed = None
        self.unsubscribed = timezone.now()
        self.unsubscribe_method = method
        self.save()
        unsubscribed.send(sender=self)


UNSUBSCRIBE_REASONS = [
    ("too_much", _("I received too many emails")),
    ("expected_updates", _("I expected more updates regarding certain campaings")),
    ("specific_request", _("I only signed up regarding a specific FOI request")),
    ("not_interested", _("The topics are not interesting to me")),
    ("dislike", _("I don't like your work anymore")),
    ("other", _("Other")),
]


class UnsubscribeFeedback(models.Model):
    reason = models.CharField(max_length=50, choices=UNSUBSCRIBE_REASONS)
    comment = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    newsletter = models.ForeignKey(Newsletter, on_delete=models.CASCADE)

    # only stored for one hour, to prevent spam
    subscriber = models.ForeignKey(
        Subscriber, blank=True, null=True, on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _("Newsletter Unsubscribe Feedback")
        constraints = [
            models.UniqueConstraint(
                fields=["subscriber", "newsletter"], name="unique_feedback_subscriber"
            )
        ]


class NewsletterCMSPlugin(CMSPlugin):
    newsletter = models.ForeignKey(
        Newsletter, related_name="+", on_delete=models.CASCADE, null=True, blank=True
    )
    fallback = models.BooleanField(default=False)

    def __str__(self):
        return str(self.newsletter)
