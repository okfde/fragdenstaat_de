import re

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string
from django.template import Template, Context
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from cms.models.fields import PlaceholderField
from cms.models.pluginmodel import CMSPlugin

from froide.helper.email_sending import EmailContent, mail_registry

from fragdenstaat_de.fds_cms.utils import get_request

from .utils import render_text

EMAIL_TEMPLATE_CHOICES = [
    ('', _('Default template'))
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
        ordering = ('name',)
        verbose_name = _('email template')
        verbose_name_plural = _('email templates')

    def __str__(self):
        return self.name

    def get_template(self, name='base.html'):
        template_base = self.template
        if template_base == '':
            template_base = 'default'
        return 'email/{}/{}'.format(template_base, name)

    def render_email_html(self, request=None):
        if request is None:
            request = get_request()
        context = {
            'placeholder': self.email_body,
            'object': self,
            'template': self.template
        }
        safe_html = render_to_string(
            'fds_mailing/render_base.html',
            context=context,
            request=request
        )
        # Call strip marks it unsafe again!
        return safe_html.strip()

    def update_context(self, ctx):
        ctx.update({
            'subject': self.subject
        })

    def get_body_html(self, context=None):
        template_str = self.render_email_html()
        if context is None:
            context = {}
        self.update_context(context)
        template = Template(template_str)
        html = template.render(Context(context))
        if '{{' in html or '}}' in html:
            raise ValueError('Likely variable definition broken')
        return html

    def render_email_text(self):
        text = ''
        if self.text:
            text = self.text
        elif self.email_body:
            text = render_text(self, self.email_body)
        return COLLAPSE_NEWLINES.sub('\r\n\r\n', text)

    def get_body_text(self, context=None):
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
        if '{{' in html or '}}' in html:
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

    def get_email_content(self, context):
        if self.mail_intent:
            intent = mail_registry.get_intent(self.mail_intent)
            if intent is not None:
                context = intent.get_context(context)
        ctx = Context(context)
        subject = self.subject_template.render(ctx)
        text = self.get_body_text(context)
        html = self.get_body_html(context)
        return EmailContent(subject, text, html)

    def get_email_bytes(self, context, recipients=None):
        if recipients is None:
            if context.get('request'):
                recipients = [context['request'].user.email]

        content = self.get_email_content(context)
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
