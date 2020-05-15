import logging
import re

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.template import Template, Context
from django.core.mail import EmailMultiAlternatives, mail_managers
from django.conf import settings
from django.contrib.auth import get_user_model

from cms.models.fields import PlaceholderField
from cms.models.static_placeholder import StaticPlaceholder
from cms.models.pluginmodel import CMSPlugin

from filer.fields.image import FilerImageField
from newsletter.models import Newsletter

from froide.helper.email_sending import EmailContent, mail_registry, send_mail
from froide.helper.email_utils import make_address

from fragdenstaat_de.fds_cms.utils import get_request
from fragdenstaat_de.fds_donation.models import Donor
from fragdenstaat_de.fds_newsletter.models import MailingSubscription

from .utils import render_text


User = get_user_model()
logger = logging.getLogger()


EMAIL_TEMPLATE_CHOICES = [
    ('', _('Default template')),
    ('newsletter', _('Newsletter template'))
]

COLLAPSE_NEWLINES = re.compile(r'((?:\r?\n){3,})')


class EmailTemplate(models.Model):
    name = models.CharField(max_length=255)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(default=timezone.now)
    category = models.CharField(
        max_length=30, blank=True
    )
    subject = models.CharField(max_length=255, blank=True)
    text = models.TextField(blank=True)

    email_body = PlaceholderField('email_body')

    template = models.CharField(
        max_length=255, blank=True,
        choices=EMAIL_TEMPLATE_CHOICES
    )
    active = models.BooleanField(default=False)
    mail_intent = models.CharField(
        max_length=255, blank=True
    )

    class Meta:
        ordering = ('-created',)
        verbose_name = _('email template')
        verbose_name_plural = _('email templates')

    def __str__(self):
        return self.name

    def get_template(self, name='base.html'):
        template_base = self.template
        if template_base == '':
            template_base = 'default'
        return 'email/{}/{}'.format(template_base, name)

    def get_mail_intent_app(self):
        if not self.mail_intent:
            return
        return self.mail_intent.split('/', 1)[0]

    def get_extra_placeholder_name(self):
        mail_intent_app = self.get_mail_intent_app()
        if not mail_intent_app:
            return
        return "email_extra_{}".format(mail_intent_app)

    def render_email_html(self, request=None, context=None,
                          template='fds_mailing/render_base.html'):
        if request is None:
            request = get_request()
        ctx = {
            'placeholder': self.email_body,
            'object': self,
            'template': self.template,
            'extra_email_placeholder': self.get_extra_placeholder_name()
        }
        if context is not None:
            ctx.update(context)
        safe_html = render_to_string(
            template,
            context=ctx,
            request=request
        )
        # Call strip marks it unsafe again!
        return safe_html.strip()

    def update_context(self, ctx):
        ctx.update({
            'subject': self.subject
        })

    def get_body_html(self, context=None, preview=False,
                      template='fds_mailing/render_base.html'):
        if context is None:
            context = {}
        self.update_context(context)
        template_str = self.render_email_html(
            context=context, template=template
        )
        template = Template(template_str)
        html = template.render(Context(context))
        if '{{' in html or '}}' in html and not preview:
            raise ValueError('Likely variable definition broken')
        return html

    def render_email_text(self):
        text = ''
        if self.text:
            text = self.text
        elif self.email_body:
            text = render_text(self.email_body)
        extra_placeholder = self.get_extra_placeholder_name()
        if extra_placeholder:
            try:
                sp = StaticPlaceholder.objects.filter(
                    code=extra_placeholder
                ).select_related('public').get()
                text = '{}\r\n\r\n{}'.format(
                    text, render_text(sp.public)
                )
            except StaticPlaceholder.DoesNotExist:
                pass
        return COLLAPSE_NEWLINES.sub('\r\n\r\n', text)

    def get_body_text(self, context=None, preview=False):
        template_str = self.render_email_text()
        template_str = '{top}{body}{bottom}{footer}'.format(
            top='{% autoescape off %}',
            body=template_str,
            bottom='{% endautoescape %}',
            footer='\r\n\r\n{% include "emails/footer.txt" %}'
        )
        if context is None:
            context = {}
        self.update_context(context)
        template = Template(template_str)
        html = template.render(Context(context))
        if '{{' in html or '}}' in html and not preview:
            raise ValueError('Likely variable definition broken')
        return html

    @property
    def subject_template(self):
        return Template('{}{}{}'.format(
            '{% autoescape off %}',
            self.subject,
            '{% endautoescape %}',
        ))

    def get_context_vars(self):
        intent = mail_registry.get_intent(self.mail_intent)
        context_vars = []
        if intent:
            context_vars.extend(intent.context_vars)
            context_vars.extend(intent.get_context({}, preview=True).keys())
        return context_vars

    def get_email_content(self, context, preview=False):
        if self.mail_intent:
            intent = mail_registry.get_intent(self.mail_intent)
            if intent is not None:
                context = intent.get_context(context)
        ctx = Context(context)
        subject = self.subject_template.render(ctx)
        text = self.get_body_text(context, preview=preview)
        html = self.get_body_html(context, preview=preview)
        return EmailContent(subject, text, html)

    def get_email_bytes(self, context, recipients=None):
        if recipients is None:
            if context.get('request'):
                recipients = [context['request'].user.email]

        content = self.get_email_content(context, preview=True)
        email = EmailMultiAlternatives(
            content.subject, content.text,
            settings.DEFAULT_FROM_EMAIL, recipients
        )
        email.attach_alternative(
            content.html,
            "text/html"
        )
        return email.message().as_bytes()


class VariableTemplateMixin:
    def get_context(self):
        return {
            key: getattr(self, key) or '{{ %s }}' % key
            for key in self.context_vars
        }


class EmailActionCMSPlugin(VariableTemplateMixin, CMSPlugin):
    heading = models.CharField(max_length=255, blank=True)
    action_url = models.CharField(max_length=255, blank=True)
    action_label = models.CharField(max_length=255, blank=True)

    context_vars = ['heading', 'action_url', 'action_label']

    def __str__(self):
        return str(self.heading)


class EmailSectionCMSPlugin(VariableTemplateMixin, CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    context_vars = ['title']

    def __str__(self):
        return str(self.title)


class EmailStoryCMSPlugin(VariableTemplateMixin, CMSPlugin):
    heading = models.CharField(max_length=255, blank=True)
    url = models.URLField(max_length=255, blank=True)
    label = models.CharField(max_length=255, blank=True)

    context_vars = ['heading', 'url', 'label']

    def __str__(self):
        return str(self.heading)


class EmailHeaderCMSPlugin(VariableTemplateMixin, CMSPlugin):
    label = models.CharField(max_length=255)
    color = models.CharField(max_length=10, blank=True)

    image = FilerImageField(null=True, blank=True, default=None,
        on_delete=models.SET_NULL, verbose_name=_("image"))

    context_vars = ['label', 'image', 'color']

    def __str__(self):
        return self.label


class Mailing(models.Model):
    name = models.CharField(max_length=255)
    email_template = models.ForeignKey(
        EmailTemplate, null=True, on_delete=models.SET_NULL
    )
    newsletter = models.ForeignKey(
        Newsletter, blank=True, null=True, on_delete=models.SET_NULL
    )
    sender_name = models.CharField(max_length=255)
    sender_email = models.EmailField(
        max_length=255, default=settings.SITE_EMAIL
    )

    created = models.DateTimeField(default=timezone.now, editable=False)

    publish = models.BooleanField(
        default=True, verbose_name=_('publish'),
        help_text=_('Publish in archive.'), db_index=True
    )

    ready = models.BooleanField(
        default=False, verbose_name=_('ready'),
    )
    submitted = models.BooleanField(
        default=False, verbose_name=_('submitted'),
        editable=False
    )
    sending_date = models.DateTimeField(
        verbose_name=_('sending date'), blank=True, null=True
    )
    sent_date = models.DateTimeField(
        verbose_name=_('sent date'), blank=True, null=True,
        editable=False
    )
    sent = models.BooleanField(
        default=False, verbose_name=_('sent'),
        editable=False
    )
    sending = models.BooleanField(
        default=False, verbose_name=_('sending'),
        editable=False
    )

    class Meta:
        ordering = ('-created',)
        verbose_name = _('mailing')
        verbose_name_plural = _('mailings')

    def __str__(self):
        return self.name

    def get_sender(self):
        return make_address(self.sender_email, name=self.sender_name)

    def get_email_context(self):
        ctx = {
            'mailing': self,
            'newsletter': self.newsletter,
        }
        return ctx

    def finalize(self):
        from newsletter.models import Subscription

        if self.newsletter:
            # Remove and re-add all newsletter recipients
            self.recipients.all().delete()
            subscriptions = Subscription.objects.filter(
                newsletter=self.newsletter, subscribed=True
            )
            for subscription in subscriptions:
                MailingMessage.objects.create(
                    mailing=self,
                    subscription=subscription,
                    name=subscription.name or '',
                    email=subscription.email
                )
            return
        for recipient in self.recipients.all():
            recipient.finalize()
            recipient.save()

    def send(self):
        if self.sending or self.sent or not self.submitted:
            return

        recipients = self.recipients.all()

        if self.newsletter:
            # Force limit to selected newsletter
            recipients = recipients.filter(
                subscription__newsletter=self.newsletter,
                subscription__subscribed=True
            )

        logger.info(
            _("Sending %(mailing)s to %(count)d people"),
            {'mailing': self, 'count': recipients.count()}
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
            mail_managers(
                'Sending out {} partly failed'.format(self.name),
                ''
            )

        finally:
            self.sending = False
            self.save()


class MailingMessage(models.Model):
    mailing = models.ForeignKey(
        Mailing, on_delete=models.CASCADE,
        related_name='recipients'
    )

    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(max_length=255)

    sent = models.DateTimeField(null=True, blank=True)
    bounced = models.BooleanField(default=False)

    message = models.TextField(blank=True)

    subscription = models.ForeignKey(
        MailingSubscription, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    donor = models.ForeignKey(
        Donor, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    user = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ('-sent',)
        verbose_name = _('mailing message')
        verbose_name_plural = _('mailing messages')

    def __str__(self):
        return 'MailingRecipient  %s (%s)' % (self.email, self.mailing)

    def get_email_context(self):
        ctx = {}
        for obj in (self.subscription, self.donor, self.user):
            if hasattr(obj, 'get_email_context'):
                ctx.update(obj.get_email_context())
        return ctx

    def finalize(self):
        if self.donor:
            self.name = self.donor.get_full_name()
            self.email = self.donor.email
        elif self.user:
            self.name = self.user.get_full_name()
            self.email = self.user.email

    def send_message(self, mailing_context=None, email_template=None):
        assert self.sent is None

        if not self.email:
            self.delete()
            return

        context = self.get_email_context()
        if mailing_context is not None:
            context.update(mailing_context)
        if email_template is None:
            email_template = self.mailing.email_template

        email_content = email_template.get_email_content(context)

        extra_kwargs = {
            'queue': settings.EMAIL_BULK_QUEUE
        }
        if email_content.html:
            extra_kwargs['html'] = email_content.html

        unsubscribe_reference = context.get('unsubscribe_reference')

        try:
            logger.debug('Sending mailing message to: %s.', self)

            send_mail(email_content.subject, email_content.text,
                make_address(self.email, name=self.name),
                from_email=self.mailing.get_sender(),
                unsubscribe_reference=unsubscribe_reference,
                **extra_kwargs
            )
            self.sent = timezone.now()
            self.save()

        except Exception as e:
            logger.error(
                'Mailing message %s failed with error: %s' % (self, e)
            )
