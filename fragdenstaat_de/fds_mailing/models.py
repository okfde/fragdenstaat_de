import logging
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, mail_managers
from django.db import models, transaction
from django.db.models.query import QuerySet
from django.template import Context, Template
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from cms.models.fields import PlaceholderRelationField
from cms.models.pluginmodel import CMSPlugin
from cms.utils.placeholder import get_placeholder_from_slot
from djangocms_frontend.fields import AttributesField
from filer.fields.image import FilerImageField
from flowcontrol.models import ActionBase
from mjml import mjml2html

from froide.helper.email_sending import EmailContent, mail_registry, send_mail
from froide.helper.email_utils import make_address

from fragdenstaat_de.fds_cms.utils import get_alias_placeholder, get_request
from fragdenstaat_de.fds_donation.models import Donor
from fragdenstaat_de.fds_newsletter.models import Newsletter, Segment, Subscriber
from fragdenstaat_de.fds_newsletter.utils import get_subscribers

from . import mailing_submitted
from .pixel_log import generate_random_unique_pixel_url
from .utils import get_url_tagger, render_text, render_web_html

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
            "base_template": self.get_base_template(),
            "email_template": self,
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

    def render_email_web_html(self, context=None):
        if context is None:
            context = {}
        return render_web_html(self.email_body, context)

    def get_body_web_html(self):
        context = {}
        self.update_context(context)
        template_str = self.render_email_web_html(context=context)
        template = Template(template_str)
        html = template.render(Context(context))
        return html

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

    def send_to_user(self, user):
        context = {"user": user, "name": user.get_full_name()}
        return self.send(user.email, context=context)

    def send(self, email_address, context=None, **extra_kwargs):
        if not self.active:
            return
        if context is None:
            context = {}

        sent_via_continuous = self.send_via_continuous_mailing(
            email_address, context=context
        )
        if sent_via_continuous:
            return sent_via_continuous

        email_content = self.get_email_content(context)

        if email_content.html:
            extra_kwargs["html"] = email_content.html

        send_mail(
            email_content.subject,
            email_content.text,
            email_address,
            **extra_kwargs,
        )

    def send_via_continuous_mailing(self, email_address, context=None):
        if not self.active:
            return False

        try:
            mailing = ContinuousMailing.objects.get(
                email_template=self,
                ready=True,
            )
        except ContinuousMailing.DoesNotExist:
            return False
        message = mailing.create_message(email_address, context=context)
        return message.send(mailing_context=context)

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


class EmailButtonCMSPlugin(VariableTemplateMixin, CMSPlugin):
    action_url = models.CharField(max_length=255, blank=True)
    action_label = models.CharField(max_length=255, blank=True)

    attributes = AttributesField()

    context_vars = ["action_url", "action_label"]
    empty_vars = {}

    def __str__(self):
        return str(self.action_label)


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


class MailingBaseManager(models.Manager):
    def get_tracked(self):
        return (
            self.get_queryset()
            .filter(
                tracking=True,
                submitted=True,
            )
            .filter(models.Q(sending=True) | models.Q(sent=True))
        )


class MailingManager(MailingBaseManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_continuous=False)


class PublishedMailingManager(MailingManager):
    def get_queryset(self) -> QuerySet:
        return (
            super()
            .get_queryset()
            .filter(
                publish=True,
                ready=True,
                submitted=True,
            )
            .filter(models.Q(sending=True) | models.Q(sent=True))
        )


class Mailing(models.Model):
    name = models.CharField(max_length=255)
    is_continuous = models.BooleanField(
        default=False,
        verbose_name=_("is continuous"),
        help_text=_(
            "This mailing is a continuous mailing that tracks transactional messages."
        ),
    )
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

    all_mailings = MailingBaseManager()
    objects = MailingManager()
    published = PublishedMailingManager()

    class Meta:
        ordering = ("-created",)
        verbose_name = _("mailing")
        verbose_name_plural = _("mailings")

        constraints = [
            models.UniqueConstraint(
                fields=["email_template"],
                condition=models.Q(is_continuous=True, ready=True),
                name="unique_continuous_mailing_emailtemplate",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.is_continuous:
            if self.publish:
                raise ValidationError(
                    _("Continuous mailings cannot be published in the archive.")
                )

    def get_absolute_url(self):
        if self.newsletter and self.publish and self.sending_date:
            return reverse(
                "newsletter_archive_detail",
                kwargs={
                    "newsletter_slug": self.newsletter.slug,
                    "year": self.sending_date.year,
                    "month": self.sending_date.month,
                    "day": self.sending_date.day,
                    "pk": self.pk,
                },
            )
        return ""

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
            html = url_tagger(html, html_entities=True)

        return EmailContent(email_content.subject, text, html)

    def submit(self, user):
        from .tasks import send_mailing

        self.submitted = True
        if not self.sending_date:
            self.sending_date = timezone.now()
        self.sender_user = user
        self.save()

        transaction.on_commit(
            lambda: send_mailing.apply_async(
                (self.id, self.sending_date),
                eta=self.sending_date,
                retry=False,
            )
        )
        mailing_submitted.send(sender=self, mailing=self)

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
                recipient.send(context)

            self.sent = True
            self.sent_date = timezone.now()

        except Exception:
            logger.exception("Mailing %s sending failed", self.name)
            mail_managers("Sending out {} partly failed".format(self.name), "")

        finally:
            self.sending = False
            self.save()


class ContinuousMailingManager(MailingBaseManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_continuous=True)


class ContinuousMailing(Mailing):
    objects = ContinuousMailingManager()

    class Meta:
        proxy = True
        verbose_name = _("continuous mailing")
        verbose_name_plural = _("continuous mailings")

    def send(self):
        raise ValueError("Cannot send a continuous mailing directly.")

    def create_message(self, email_address, context=None):
        if context is None:
            context = {}

        message = MailingMessage.objects.create(
            mailing=self,
            email=email_address,
            user=context.get("user"),
            name=context.get("name", ""),
            is_continuous=True,
        )
        if context.get("user"):
            MailingMessageReference.objects.create_with_object(message, context["user"])

        return message


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
    is_continuous = models.BooleanField(
        default=False,
        verbose_name=_("is continuous"),
        help_text=_(
            "This message is part of a continuous mailing that tracks transactional messages."
        ),
    )

    class Meta:
        ordering = ("-sent",)
        verbose_name = _("mailing message")
        verbose_name_plural = _("mailing messages")
        constraints = [
            models.UniqueConstraint(
                fields=["mailing", "email"],
                condition=models.Q(is_continuous=False),
                name="unique_mailing_email",
            ),
            models.UniqueConstraint(
                fields=["mailing", "subscriber"],
                condition=models.Q(subscriber__isnull=False),
                name="unique_mailing_subscriber",
            ),
            models.UniqueConstraint(
                fields=["mailing", "user"],
                condition=models.Q(user__isnull=False, is_continuous=False),
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

        if "unsubscribe_reference" in ctx:
            ctx["unsubscribe_reference"] += "-%s" % self.mailing.mailing_ident
        if self.subscriber:
            # Set unsubscribe URL again with unsubscribe reference
            ctx["unsubscribe_url"] = self.subscriber.get_unsubscribe_url(
                reference=self.mailing.mailing_ident
            )

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

    def send(self, mailing_context=None, extra_kwargs=None):
        assert self.sent is None

        if not self.email:
            self.delete()
            return
        if not self.mailing.sending:
            logger.error("Mailing %s not sending, not sending message", self.mailing)
            return

        context = self.get_email_context()
        if mailing_context is not None:
            context.update(mailing_context)

        email_content = self.mailing.get_email_content(context)

        if extra_kwargs is None:
            extra_kwargs = {}

        if not self.mailing.is_continuous:
            extra_kwargs.update({"queue": settings.EMAIL_BULK_QUEUE})

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
            return False
        return True


class MailingMessageReferenceManager(models.Manager):
    def create_with_object(self, mailing_message, content_object, content_type=None):
        if content_type is None:
            content_type = ContentType.objects.get_for_model(content_object)
        return self.create(
            mailing_message=mailing_message,
            content_type=content_type,
            object_id=content_object.pk,
        )


class MailingMessageReference(models.Model):
    mailing_message = models.ForeignKey(MailingMessage, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    objects = MailingMessageReferenceManager()

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
        help_text=_("0 means all the mailings. Should be divisible by 3."),
    )


class ConditionCMSPlugin(CMSPlugin):
    context_key = models.CharField(
        max_length=255,
        help_text=_("Key to check in the context."),
    )
    context_value = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Optional value to check on key. Checks for presence if empty."),
    )
    negate = models.BooleanField(
        default=False,
        help_text=_("Negate the condition."),
    )

    def __str__(self):
        return "%s%s%s%s" % (
            "not " if self.negate else "",
            self.context_key,
            " == " if self.context_value else "",
            self.context_value,
        )


class DelayMailActionConfig(ActionBase):
    delay_days = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of days to wait between emails."),
    )
    max_delay_days = models.PositiveIntegerField(
        default=0,
        help_text=_("Maximum number of days to wait between emails. 0 means no limit."),
    )

    def __str__(self):
        return _("Delay by {delay_days} days, max {max_delay_days} days total").format(
            delay_days=self.delay_days, max_delay_days=self.max_delay_days
        )


class SendMailActionConfig(ActionBase):
    email_template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.CASCADE,
        help_text=_("Email template to use for this action."),
    )

    def __str__(self):
        return _("Template: {template}").format(template=self.email_template)
