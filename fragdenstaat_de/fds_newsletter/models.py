import logging

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.models import Site
from django.utils.translation import ugettext as _
from django.utils import timezone

from newsletter.models import Newsletter, Subscription, Submission as BaseSubmission
from newsletter.utils import ACTIONS

from froide.helper.email_sending import send_mail
from froide.helper.email_utils import make_address

from fragdenstaat_de.fds_mailing.models import EmailTemplate

from .utils import REFERENCE_PREFIX


logger = logging.getLogger(__name__)


def get_email_context(subscription, submission=None, mailing=None):
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
        'MEDIA_URL': settings.MEDIA_URL
    }
    if submission is not None:
        context.update({
            'submission': submission,
            'message': submission.message,
            'newsletter': submission.newsletter,
            'date': submission.publish_date,
        })

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


class Mailing(models.Model):
    email_template = models.ForeignKey(EmailTemplate, null=True, on_delete=models.SET_NULL)
    newsletter = models.ForeignKey(Newsletter, null=True, on_delete=models.SET_NULL)
    sender_name = models.CharField(max_length=255, blank=True)

    created = models.DateTimeField(default=timezone.now, editable=False)

    subscriptions = models.ManyToManyField(
        Subscription,
        help_text=_('If you select none, the system will automatically find '
                    'the subscribers for you.'),
        verbose_name=_('recipients'),
        blank=True,
        limit_choices_to={'subscribed': True}
    )

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
        verbose_name = _('mailing')
        verbose_name_plural = _('mailings')

    def __str__(self):
        return str(self.email_template)

    def send(self):
        if self.sending or self.sent or not self.submitted:
            return

        subscriptions = self.subscriptions.filter(
            subscribed=True
        )
        if self.newsletter:
            # Force limit to selected newsletter
            subscriptions = subscriptions.filter(newsletter=self.newsletter)

        logger.info(
            _(u"Submitting %(submission)s to %(count)d people"),
            {'submission': self, 'count': subscriptions.count()}
        )
        self.sending = True
        self.save()

        try:
            for subscription in subscriptions:
                self.send_message(subscription)
            self.sent = True
            self.sent_date = timezone.now()

        finally:
            self.sending = False
            self.save()

    def send_message(self, subscription):
        context = get_email_context(subscription, mailing=self)

        email_content = self.email_template.get_email_content(context)

        extra_kwargs = {
            'queue': settings.EMAIL_BULK_QUEUE
        }
        if email_content.html:
            extra_kwargs['html'] = email_content.html

        if self.sender_name:
            sender_name = self.sender_name
        elif self.newsletter:
            sender_name = self.newsletter.sender

        if self.newsletter:
            email = self.newsletter.email
            sender = make_address(email, name=sender_name)
        else:
            sender = settings.DEFAULT_FROM_EMAIL

        recipient = make_address(subscription.email, name=subscription.name)

        try:
            logger.debug('Submitting message to: %s.', subscription)

            send_mail(
                email_content.subject,
                email_content.text,
                recipient,
                from_email=sender,
                unsubscribe_reference='{prefix}{pk}'.format(
                    prefix=REFERENCE_PREFIX, pk=subscription.id
                ),
                **extra_kwargs
            )

        except Exception as e:
            # TODO: Test coverage for this branch.
            logger.error(
                'Message %(subscription)s failed with error: %(error)s', {
                    'subscription': subscription,
                    'error': e
                })


class Submission(BaseSubmission):
    class Meta:
        proxy = True

    def send_message(self, subscription):

        context = get_email_context(subscription, submission=self)

        subject = self.message.subject_template.render(context).strip()
        body = self.message.text_template.render(context)

        extra_kwargs = {
            'queue': settings.EMAIL_BULK_QUEUE
        }
        if self.message.html_template:
            extra_kwargs['html'] = self.message.html_template.render(context)

        try:
            logger.debug(
                _(u'Submitting message to: %s.'),
                subscription
            )

            send_mail(subject, body, make_address(subscription.email, name=subscription.name),
                from_email=self.newsletter.get_sender(),
                unsubscribe_reference='{prefix}{pk}'.format(
                    prefix=REFERENCE_PREFIX, pk=subscription.id
                ),
                **extra_kwargs
            )

        except Exception as e:
            # TODO: Test coverage for this branch.
            logger.error(
                _(u'Message %(subscription)s failed '
                         u'with error: %(error)s'),
                {'subscription': subscription,
                 'error': e}
            )


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
        u'Activation email sent for action "%(action)s" to %(subscriber)s '
        u'with activation code "%(action_code)s".', {
            'action_code': self.activation_code,
            'action': action,
            'subscriber': self
        }
    )

# FIXME: monkey patch subscription


Subscription.send_activation_email = send_activation_email
