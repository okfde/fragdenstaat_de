import logging

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.crypto import get_random_string

from newsletter.models import Subscription as NLSubscription
from newsletter.utils import ACTIONS

from froide.helper.email_sending import send_mail
from froide.helper.email_sending import mail_registry

from .utils import REFERENCE_PREFIX


logger = logging.getLogger(__name__)


subscriber_confirm_email = mail_registry.register(
    'fds_newsletter/email/subscriber_confirm',
    (
        'name', 'newsletter',
    )
)


def get_email_context(subscription):
    if subscription.user:
        unsubscribe_url = subscription.user.get_autologin_url(
            reverse('account-settings')
        ) + '#newsletter'
    else:
        unsubscribe_url = (
            settings.SITE_URL + subscription.unsubscribe_activate_url()
        )
    site = Site.objects.get_current()
    context = {
        'subscription': subscription,
        'newsletter': subscription.newsletter,
        'date': subscription.subscribe_date,
        'site': site,
        'site_name': settings.SITE_NAME,
        'site_url': settings.SITE_URL,
        'domain': site.domain,
        'unsubscribe_url': unsubscribe_url,
        'STATIC_URL': settings.STATIC_URL,
        'MEDIA_URL': settings.MEDIA_URL,
        'unsubscribe_reference': '{prefix}{pk}'.format(
            prefix=REFERENCE_PREFIX, pk=subscription.id
        )
    }

    if subscription.user:
        user = subscription.user
        context.update({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'name': user.get_full_name(),
            'login_url': user.get_autologin_url('/'),
        })
    else:
        context.update({
            'name': subscription.name,
        })
    return context


class NewsletterManager(models.Manager):
    def get_visible(self):
        return self.filter(visible=True)


class Newsletter(models.Model):
    title = models.CharField(
        max_length=200, verbose_name=_('newsletter title')
    )
    slug = models.SlugField(db_index=True, unique=True)
    url = models.URLField(blank=True)

    email = models.EmailField(
        verbose_name=_('e-mail'), help_text=_('Sender e-mail')
    )
    sender = models.CharField(
        max_length=200, verbose_name=_('sender'), help_text=_('Sender name')
    )

    visible = models.BooleanField(
        default=True, verbose_name=_('visible')
    )

    objects = NewsletterManager()

    class Meta:
        verbose_name = _('newsletter')
        verbose_name_plural = _('newsletters')

    def __str__(self):
        return self.title


class Subscription(models.Model):
    newsletter = models.ForeignKey(
        Newsletter, verbose_name=_('newsletter'), on_delete=models.CASCADE
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, verbose_name=_('user'),
        on_delete=models.CASCADE, related_name='+'
    )

    name = models.CharField(
        db_column='name', max_length=30, blank=True, null=True,
        verbose_name=_('name'), help_text=_('optional')
    )
    subscriber_email = models.EmailField(
        db_column='email', verbose_name=_('e-mail'), db_index=True,
        blank=True, null=True
    )
    send_html = models.BooleanField(default=True)

    create_date = models.DateTimeField(editable=False, default=timezone.now)

    last_activation_sent = models.DateTimeField(null=True, blank=True)

    activation_code = models.CharField(
        verbose_name=_('activation code'), max_length=40,
        default=lambda: get_random_string(length=40)
    )

    subscribed = models.NullBooleanField(
        default=None, verbose_name=_('subscribed'), db_index=True
    )
    subscribe_date = models.DateTimeField(
        verbose_name=_("subscribe date"), null=True, blank=True
    )

    unsubscribe_date = models.DateTimeField(
        verbose_name=_("unsubscribe date"), null=True, blank=True
    )

    reference = models.CharField(max_length=255, blank=True)
    keyword = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = _('newsletter subscription')
        verbose_name_plural = _('newsletter subscriptions')
        ordering = ('-subscribe_date',)
        constraints = [
            models.UniqueConstraint(
                fields=['newsletter', 'user'],
                condition=models.Q(user__isnull=False),
                name='unique_user_newsletter'
            ),
            models.UniqueConstraint(
                fields=['newsletter', 'email'],
                condition=models.Q(email__isnull=False),
                name='unique_email_newsletter'
            ),
            models.CheckConstraint(
                check=models.Q(
                    user__isnull=True, email__isnull=False
                ) | models.Q(user__isnull=False, email__isnull=True),
                name='newsletter_subscription_user_email')
        ]

    def __str__(self):
        return '<{}> - {}'.format(
            self.email, self.newsletter
        )

    @property
    def email(self):
        if self.user:
            return self.user.email
        return self.subscriber_email

    def send_activation_email(self, action):

        context = get_email_context(self)

        subscriber_confirm_email.send(
            email=self.email,
            user=self.user,
            context=context,
            ignore_active=True, priority=True
        )


class MailingSubscription(NLSubscription):
    class Meta:
        proxy = True

    def get_email_context(self):
        return get_email_context(self)


def send_activation_email(self, action):
    assert action in ACTIONS, 'Unknown action: %s' % action

    (subject_template, text_template, html_template) = \
        self.newsletter.get_templates(action)

    context = get_email_context(self)

    subject = subject_template.render(context).strip()
    body = text_template.render(context)

    extra_kwargs = {}
    if html_template:
        extra_kwargs['html'] = html_template.render(context)

    send_mail(subject, body, self.email,
        from_email=self.newsletter.get_sender(),
        **extra_kwargs
    )

    logger.debug(
        'Activation email sent for action "%(action)s" to %(subscriber)s '
        'with activation code "%(action_code)s".', {
            'action_code': self.activation_code,
            'action': action,
            'subscriber': self
        }
    )
