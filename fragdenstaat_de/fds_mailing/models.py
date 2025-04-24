import logging
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMultiAlternatives, mail_managers
from django.db import models
from django.db.models.query import QuerySet
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from cms.models.fields import PlaceholderRelationField
from cms.models.pluginmodel import CMSPlugin
from cms.utils.placeholder import get_placeholder_from_slot
from filer.fields.image import FilerImageField
from mjml import mjml2html

from froide.helper.email_sending import EmailContent, mail_registry, send_mail
from froide.helper.email_utils import make_address

from fragdenstaat_de.fds_cms.utils import get_alias_placeholder, get_request
from fragdenstaat_de.fds_donation.models import Donor
from fragdenstaat_de.fds_newsletter.models import Newsletter, Segment, Subscriber
from fragdenstaat_de.fds_newsletter.utils import get_subscribers

from .utils import generate_random_unique_pixel_url, get_url_tagger, render_text

User = get_user_model()
logger = logging.getLogger()


EMAIL_TEMPLATE_CHOICES = [
    ("", _("Default template")),
    ("newsletter", _("Newsletter template")),
    ("formal", _("Formal email template")),
    ("mjml", _("MJML email template")),
]

COLLAPSE_NEWLINES = re.compile(r"((?:\r?\n){3,})")


class EmailTemplate(models.Model):
    name = models.CharField(max_length=255)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(default=timezone.now)
    category = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    preheader = models.CharField(max_length=255, blank=True)
    text = models.TextField(blank=True)

    placeholders = PlaceholderRelationField()

    template = models.CharField(
        max_length=255, blank=True, choices=EMAIL_TEMPLATE_CHOICES
    )
    active = models.BooleanField(default=False)
    mail_intent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-created",)
        verbose_name = _("email template")
        verbose_name_plural = _("email templates")

    def __str__(self):
        return self.name

    @cached_property
    def email_body(self):
        return get_placeholder_from_slot(self.placeholders, "email_body")

    def get_template(self):
        return "fds_mailing/placeholders.html"

    def get_base_template(self, name="base.html"):
        template_base = self.template
        if template_base == "":
            template_base = "default"
        if template_base == "mjml":
            name = name.replace(".html", ".mjml")
        return "email/{}/{}".format(template_base, name)

    def get_mail_intent_app(self):
        if not self.mail_intent:
            return
        return self.mail_intent.split("/", 1)[0]

    def get_mail_intent(self):
        if not self.mail_intent:
            return
        return mail_registry.get_intent(self.mail_intent)

    def get_extra_placeholder_name(self):
        mail_intent_app = self.get_mail_intent_app()
        if not mail_intent_app:
            return
        return "email_extra_{}".format(mail_intent_app)

    def render_email_html(
        self, request=None, context=None, template="fds_mailing/render_base.html"
    ):
        if request is None:
            request = get_request()
        request.toolbar.set_object(self)
        ctx = {
            "placeholder": self.email_body,
            "object": self,
            "template": self.template,
            "extra_email_placeholder": self.get_extra_placeholder_name(),
        }
        if context is not None:
            ctx.update(context)
        safe_html = render_to_string(template, context=ctx, request=request)
        # Call strip marks it unsafe again!
        html = safe_html.strip()

        if "<mjml>" in html:
            html = html.replace("<p>\xa0</p>", "")
            html = mjml2html(html, disable_comments=True)
        return html

    def update_context(self, ctx):
        ctx.update({"subject": self.subject, "preheader": self.preheader})

    def get_body_html(
        self, context=None, preview=False, template="fds_mailing/render_base.html"
    ):
        if context is None:
            context = {}
        self.update_context(context)
        template_str = self.render_email_html(context=context, template=template)
        template = Template(template_str)
        html = template.render(Context(context))
        if "{{" in html or "}}" in html and not preview:
            raise ValueError("Likely variable definition broken")
        return html

    def render_email_text(self, context=None):
        if context is None:
            context = {}
        text = ""
        if self.text:
            text = self.text
        elif self.email_body:
            text = render_text(self.email_body, context)
        extra_placeholder_name = self.get_extra_placeholder_name()
        if extra_placeholder_name:
            placeholder = get_alias_placeholder(extra_placeholder_name)
            if placeholder:
                text = "{}\r\n\r\n{}".format(text, render_text(placeholder, context))
        return COLLAPSE_NEWLINES.sub("\r\n\r\n", text)

    def get_body_text(self, context=None, preview=False):
        template_str = self.render_email_text(context)
        template_str = "{top}{body}{bottom}{footer}".format(
            top="{% autoescape off %}",
            body=template_str,
            bottom="{% endautoescape %}",
            footer='\r\n\r\n{% include "emails/footer.txt" %}',
        )
        if context is None:
            context = {}
        self.update_context(context)
        template = Template(template_str)
        html = template.render(Context(context))
        if "{{" in html or "}}" in html and not preview:
            raise ValueError("Likely variable definition broken")
        return html

    @property
    def subject_template(self):
        return Template(
            "{}{}{}".format(
                "{% autoescape off %}",
                self.subject,
                "{% endautoescape %}",
            )
        )

    def get_context_vars(self):
        intent = self.get_mail_intent()
        context_vars = []
        if intent:
            context_vars.extend(intent.context_vars)
            context_vars.extend(intent.get_context({}, preview=True).keys())
        return context_vars

    def get_email_content(self, context, preview=False):
        if self.mail_intent:
            intent = self.get_mail_intent()
            if intent is not None:
                context = intent.get_context(context)
        ctx = Context(context)
        subject = self.subject_template.render(ctx)
        text = self.get_body_text(context, preview=preview)
        html = self.get_body_html(context, preview=preview)
        return EmailContent(subject, text, html)

    def send_to_user(self, user, bulk=False):
        context = {"user": user}
        email_content = self.get_email_content(context)

        extra_kwargs = {}
        if bulk:
            extra_kwargs["queue"] = settings.EMAIL_BULK_QUEUE
        if email_content.html:
            extra_kwargs["html"] = email_content.html

        send_mail(
            email_content.subject,
            email_content.text,
            make_address(user.email, name=user.get_full_name()),
            from_email=settings.DEFAULT_FROM_EMAIL,
            **extra_kwargs,
        )

    def get_email_bytes(self, context, recipients=None):
        if recipients is None:
            if context.get("request"):
                recipients = [context["request"].user.email]

        content = self.get_email_content(context, preview=True)
        email = EmailMultiAlternatives(
            content.subject, content.text, settings.DEFAULT_FROM_EMAIL, recipients
        )
        email.attach_alternative(content.html, "text/html")
        return email.message().as_bytes()


class VariableTemplateMixin:
    empty_vars = set()

    def get_context(self):
        return {
            key: getattr(self, key)
            or ("{{ %s }}" % key if key not in self.empty_vars else "")
            for key in self.context_vars
        }


class EmailActionCMSPlugin(VariableTemplateMixin, CMSPlugin):
    heading = models.CharField(max_length=255, blank=True)
    action_url = models.CharField(max_length=255, blank=True)
    action_label = models.CharField(max_length=255, blank=True)

    context_vars = ["heading", "action_url", "action_label"]
    empty_vars = {"heading"}

    def __str__(self):
        return str(self.heading)


class EmailSectionCMSPlugin(VariableTemplateMixin, CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    context_vars = ["title"]

    def __str__(self):
        return str(self.title)


class EmailStoryCMSPlugin(VariableTemplateMixin, CMSPlugin):
    heading = models.CharField(max_length=255, blank=True)
    url = models.URLField(max_length=255, blank=True)
    label = models.CharField(max_length=255, blank=True)

    context_vars = ["heading", "url", "label"]

    def __str__(self):
        return str(self.heading)


class EmailHeaderCMSPlugin(VariableTemplateMixin, CMSPlugin):
    label = models.CharField(max_length=255)
    color = models.CharField(max_length=10, blank=True)

    image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=_("image"),
    )

    context_vars = ["label", "image", "color"]

    def __str__(self):
        return self.label


class PublishedMailingManager(models.Manager):
    def get_queryset(self) -> QuerySet:
        return (
            super()
            .get_queryset()
            .filter(
                publish=True,
                ready=True,
                submitted=True,
                sent=True,
            )
        )


class Mailing(models.Model):
    name = models.CharField(max_length=255)
    email_template = models.ForeignKey(
        EmailTemplate, null=True, on_delete=models.SET_NULL
    )
    newsletter = models.ForeignKey(
        Newsletter, blank=True, null=True, on_delete=models.SET_NULL
    )
    segments = models.ManyToManyField(Segment, blank=True)
    sender_name = models.CharField(max_length=255)
    sender_email = models.EmailField(max_length=255, default=settings.SITE_EMAIL)

    sender_user = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        editable=False,
        related_name="mailings_sent",
    )
    creator_user = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        editable=False,
        related_name="mailings_created",
    )
    created = models.DateTimeField(default=timezone.now, editable=False)

    publish = models.BooleanField(
        default=False,
        verbose_name=_("publish"),
        help_text=_("Publish in archive."),
        db_index=True,
    )

    tracking = models.BooleanField(
        default=False,
        verbose_name=_("tracking"),
        help_text=_("Track opens and clicks."),
    )

    ready = models.BooleanField(
        default=False,
        verbose_name=_("ready"),
    )
    submitted = models.BooleanField(
        default=False, verbose_name=_("submitted"), editable=False
    )
    sending_date = models.DateTimeField(
        verbose_name=_("sending date"), blank=True, null=True
    )
    sent_date = models.DateTimeField(
        verbose_name=_("sent date"), blank=True, null=True, editable=False
    )
    sent = models.BooleanField(default=False, verbose_name=_("sent"), editable=False)
    sending = models.BooleanField(
        default=False, verbose_name=_("sending"), editable=False
    )

    open_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("open count"),
        help_text=_("Number of times the email was opened."),
    )
    open_log_timestamp = models.DateTimeField(
        null=True,
        blank=True,
    )

    objects = models.Manager()
    published = PublishedMailingManager()

    class Meta:
        ordering = ("-created",)
        verbose_name = _("mailing")
        verbose_name_plural = _("mailings")

    def __str__(self):
        return self.name

    def get_sender(self):
        return make_address(self.sender_email, name=self.sender_name)

    def get_email_context(self):
        ctx = {
            "mailing": self,
            "newsletter": self.newsletter,
        }
        return ctx

    def get_recipient_count(self):
        if not hasattr(self, "_recipient_count"):
            if self.newsletter:
                self._recipient_count = self.get_subscribers().count()
            else:
                self._recipient_count = self.recipients.count()
        return self._recipient_count

    def get_subscribers(self):
        return get_subscribers(self.newsletter, self.segments.all())

    def auto_populate(self):
        if not self.newsletter:
            return

        # Remove and re-add all newsletter recipients
        self.recipients.all().delete()

        for subscriber in self.get_subscribers():
            MailingMessage.objects.create(
                mailing=self,
                subscriber=subscriber,
                name=subscriber.get_name(),
                email=subscriber.get_email(),
            )

    def finalize(self):
        self.auto_populate()

        for recipient in self.recipients.all():
            recipient.finalize()
            recipient.save()

    @property
    def mailing_ident(self):
        if self.sending_date:
            date_str = self.sending_date.strftime("%Y%m%d%H%M")
            return f"mailing-{date_str}-{self.id}"
        return f"mailing--{self.id}"

    def get_email_content(self, context) -> EmailContent:
        if not self.email_template:
            raise ValueError("No email template set")

        email_content = self.email_template.get_email_content(context)

        if not self.tracking:
            return email_content

        # Add campaign param to all URLs
        url_tagger = get_url_tagger(self.mailing_ident)
        text = email_content.text
        if text:
            text = url_tagger(text)
        html = email_content.html
        if html:
            html = url_tagger(html)

        return EmailContent(email_content.subject, text, html)

    def send(self):
        if self.sending or self.sent or not self.submitted:
            return

        recipients = self.recipients.all()

        if self.newsletter:
            # Force limit to selected newsletter
            recipients = recipients.filter(
                subscriber__newsletter=self.newsletter,
                subscriber__subscribed__isnull=False,
            )

        logger.info(
            _("Sending %(mailing)s to %(count)d people"),
            {"mailing": self, "count": recipients.count()},
        )
        self.sending = True
        self.save()

        context = self.get_email_context()

        try:
            for recipient in recipients:
                recipient.send_message(context)

            self.sent = True
            self.sent_date = timezone.now()

        except Exception:
            logger.exception("Mailing %s sending failed", self.name)
            mail_managers("Sending out {} partly failed".format(self.name), "")

        finally:
            self.sending = False
            self.save()


class MailingMessage(models.Model):
    mailing = models.ForeignKey(
        Mailing, on_delete=models.CASCADE, related_name="recipients"
    )

    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(max_length=255)

    sent = models.DateTimeField(null=True, blank=True)
    bounced = models.BooleanField(default=False)

    message = models.TextField(blank=True)

    subscriber = models.ForeignKey(
        Subscriber, null=True, blank=True, on_delete=models.SET_NULL
    )
    donor = models.ForeignKey(Donor, null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ("-sent",)
        verbose_name = _("mailing message")
        verbose_name_plural = _("mailing messages")
        constraints = [
            models.UniqueConstraint(
                fields=["mailing", "email"],
                name="unique_mailing_email",
            ),
            models.UniqueConstraint(
                fields=["mailing", "subscriber"],
                condition=models.Q(subscriber__isnull=False),
                name="unique_mailing_subscriber",
            ),
            models.UniqueConstraint(
                fields=["mailing", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_mailing_user",
            ),
        ]

    def __str__(self):
        return "MailingRecipient  %s (%s)" % (self.email, self.mailing)

    def get_email_context(self):
        ctx = {"user": self.user, "donor": self.donor}
        # Try to find a user
        if not self.user and self.subscriber and self.subscriber.user:
            ctx["user"] = self.subscriber.user
        elif not self.user and self.donor and self.donor.user:
            ctx["user"] = self.donor.user

        # Try to find a donor
        if ctx["user"] and not ctx.get("donor"):
            ctx["donor"] = Donor.objects.filter(user=ctx["user"]).first()

        if self.subscriber and not ctx.get("donor"):
            ctx["donor"] = Donor.objects.filter(subscriber=self.subscriber).first()

        if not ctx["donor"] and self.subscriber and self.subscriber.email:
            ctx["donor"] = Donor.objects.filter(
                email=self.subscriber.email, email_confirmed__isnull=False
            ).first()

        for obj in (self.subscriber, ctx["donor"], ctx["user"]):
            if hasattr(obj, "get_email_context"):
                ctx.update(obj.get_email_context())
        if "name" not in ctx:
            ctx["name"] = self.name
        if "pixel_url" not in ctx and self.mailing.tracking:
            ctx["pixel_url"] = self.generate_random_unique_pixel_url()
        return ctx

    def generate_random_unique_pixel_url(self):
        return generate_random_unique_pixel_url(self.mailing.id)

    def finalize(self):
        if self.donor:
            self.name = self.donor.get_full_name()
            self.email = self.donor.email
        elif self.user:
            self.name = self.user.get_full_name()
            self.email = self.user.email
        if not self.email and self.subscriber:
            self.email = self.subscriber.get_email()
            self.name = self.subscriber.get_name()

    def send_message(self, mailing_context=None):
        assert self.sent is None

        if not self.email:
            self.delete()
            return

        context = self.get_email_context()
        if mailing_context is not None:
            context.update(mailing_context)

        email_content = self.mailing.get_email_content(context)

        extra_kwargs = {"queue": settings.EMAIL_BULK_QUEUE}
        if email_content.html:
            extra_kwargs["html"] = email_content.html

        unsubscribe_reference = context.get("unsubscribe_reference")

        try:
            logger.debug("Sending mailing message to: %s.", self)

            send_mail(
                email_content.subject,
                email_content.text,
                make_address(self.email, name=self.name),
                from_email=self.mailing.get_sender(),
                unsubscribe_reference=unsubscribe_reference,
                **extra_kwargs,
            )
            self.sent = timezone.now()
            self.save()

        except Exception as e:
            logger.error("Mailing message %s failed with error: %s" % (self, e))


class MailingMessageReference(models.Model):
    mailing_message = models.ForeignKey(MailingMessage, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self):
        return "%s - %s" % (self.mailing_message, self.content_type)

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["mailing_message", "content_type"],
                name="unique_mailing_message_content_type",
            )
        ]


class NewsletterArchiveCMSPlugin(CMSPlugin):
    newsletter = models.ForeignKey(Newsletter, on_delete=models.CASCADE)
    number_of_mailings = models.PositiveIntegerField(
        _("number of mailing"),
        default=6,
        help_text=_("0 means all the mailings. Should be devisible by 3."),
    )
