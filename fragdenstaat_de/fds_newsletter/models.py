import logging

from django.conf import settings
from django.urls import reverse
from django.contrib.sites.models import Site

from newsletter.models import Subscription
from newsletter.utils import ACTIONS

from froide.helper.email_sending import send_mail

from .utils import REFERENCE_PREFIX


logger = logging.getLogger(__name__)


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


class MailingSubscription(Subscription):
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

# FIXME: monkey patch subscription


Subscription.send_activation_email = send_activation_email
