import logging

from django.conf import settings
from django.urls import reverse
from django.contrib.sites.models import Site
from django.utils.translation import ugettext

from newsletter.models import Subscription, Submission as BaseSubmission
from newsletter.utils import ACTIONS

from froide.helper.email_sending import send_mail

logger = logging.getLogger(__name__)


def get_email_context(subscription, submission=None):
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


class Submission(BaseSubmission):
    class Meta:
        proxy = True

    def send_message(self, subscription):

        context = get_email_context(subscription, submission=self)
        extra_headers = {
            'List-Unsubscribe': context['unsubscribe_url']
        }

        subject = self.message.subject_template.render(context).strip()
        body = self.message.text_template.render(context)

        extra_kwargs = {}
        if self.message.html_template:
            extra_kwargs['html'] = self.message.html_template.render(context)

        try:
            logger.debug(
                ugettext(u'Submitting message to: %s.'),
                subscription
            )

            send_mail(subject, body, subscription.get_recipient(),
                from_email=self.newsletter.get_sender(),
                headers=extra_headers,
                **extra_kwargs
            )

        except Exception as e:
            # TODO: Test coverage for this branch.
            logger.error(
                ugettext(u'Message %(subscription)s failed '
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
