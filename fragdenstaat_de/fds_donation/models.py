import uuid
from urllib.parse import urlencode

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.utils.translation import pgettext, ugettext_lazy as _

from cms.models.pluginmodel import CMSPlugin

from django_countries.fields import CountryField

from froide.account.models import User

from froide_payment.models import Order, Payment, Subscription


INTERVAL_SETTINGS_CHOICES = [
    ('once', _('Only once')),
    ('recurring', _('Only recurring')),
    ('once_recurring', _('Both')),
]


SALUTATION_CHOICES = (
    ('', pgettext('salutation neutral', 'Hello')),
    ('formal_f', pgettext(
        'salutation female formal', 'Dear Ms.')),
    ('formal_m', pgettext(
        'salutation male formal', 'Dear Mr.')),
    ('informal_f', pgettext(
        'salutation female informal', 'Dear')),
    ('informal_m', pgettext(
        'salutation male informal', 'Dear')),
)
SALUTATION_DICT = dict(SALUTATION_CHOICES)


class Donor(models.Model):
    salutation = models.CharField(max_length=25, blank=True)
    first_name = models.CharField(max_length=256, blank=True)
    last_name = models.CharField(max_length=256, blank=True)
    company_name = models.CharField(max_length=256, blank=True)
    address = models.CharField(max_length=256, blank=True)
    city = models.CharField(max_length=256, blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    country = CountryField(blank=True)

    email = models.EmailField(blank=True, default='')

    active = models.BooleanField(default=False)
    first_donation = models.DateTimeField(default=timezone.now)
    last_donation = models.DateTimeField(default=timezone.now)

    user = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    subscription = models.ForeignKey(
        Subscription, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    email_confirmation_sent = models.DateTimeField(null=True, blank=True)
    email_confirmed = models.DateTimeField(null=True, blank=True)
    contact_allowed = models.BooleanField(default=False)
    become_user = models.BooleanField(default=False)
    receipt = models.BooleanField(default=False)

    note = models.TextField(blank=True)

    class Meta:
        ordering = ('-last_donation',)
        verbose_name = _('donor')
        verbose_name_plural = _('donors')

    def __str__(self):
        return '{} ({})'.format(
            self.get_full_name(),
            self.email
        )

    def get_full_name(self):
        return '{} {}'.format(self.first_name, self.last_name)

    def get_salutation(self):
        salutation = SALUTATION_DICT.get(self.salutation, None)
        if salutation is None:
            salutation = self.salutation
        if 'informal' in self.salutation:
            name = self.first_name
        elif 'formal' in self.salutation:
            name = self.last_name
        else:
            name = self.get_full_name()
        return '{} {}'.format(
            salutation,
            name
        )

    def get_full_address(self):
        return '\n'.join(x for x in [
            self.address,
            '{} {}'.format(self.postcode, self.city),
            self.country.name
        ] if x)

    def get_absolute_url(self):
        return reverse('fds_donation:donor', kwargs={
            'token': str(self.uuid)
        })

    def get_url(self):
        return settings.SITE_URL + self.get_absolute_url()


class Donation(models.Model):
    donor = models.ForeignKey(
        Donor, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    timestamp = models.DateTimeField(default=timezone.now)
    completed = models.BooleanField(default=False)
    amount = models.DecimalField(
        max_digits=12, decimal_places=settings.DEFAULT_DECIMAL_PLACES, default=0
    )
    received = models.BooleanField(default=False)
    email_sent = models.DateTimeField(null=True, blank=True)

    note = models.TextField()
    purpose = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=255, blank=True)

    order = models.OneToOneField(
        Order, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    payment = models.OneToOneField(
        Payment, null=True, blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ('-timestamp',)
        verbose_name = _('donation')
        verbose_name_plural = _('donations')

    def __str__(self):
        return '{} ({} - {})'.format(
            self.amount, self.timestamp, self.donor
        )

    def get_success_url(self):
        if self.donor and self.donor.user:
            return self.donor.get_absolute_url() + '?complete'
        if self.donor:
            url = reverse('fds_donation:donate-complete')
            query = {
                'email': self.donor.email.encode('utf-8'),
            }
            if self.order:
                query.update({
                    'order': self.order.get_absolute_url().encode('utf-8'),
                })
                if self.order.subscription:
                    sub_url = self.order.subscription.get_absolute_url()
                    query.update({
                        'subscription': sub_url.encode('utf-8')
                    })
            query = urlencode(query)
            return '%s?%s' % (url, query)
        if self.order:
            return self.order.get_absolute_url()
        return '/'


class DonationGift(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category_slug = models.SlugField(max_length=255, blank=True)

    class Meta:
        verbose_name = _('donation gift')
        verbose_name_plural = _('donation gifts')
        ordering = ('name',)

    def __str__(self):
        return self.name


class DonationGiftFormCMSPlugin(CMSPlugin):
    category = models.SlugField()
    next_url = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return str(self.category)


class DonationFormCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    interval = models.CharField(
        max_length=20, choices=INTERVAL_SETTINGS_CHOICES
    )
    amount_presets = models.CharField(max_length=255, blank=True)
    initial_amount = models.IntegerField(null=True, blank=True)
    initial_interval = models.IntegerField(null=True, blank=True)

    reference = models.CharField(blank=True, max_length=255)
    purpose = models.CharField(blank=True, max_length=255)

    form_action = models.CharField(max_length=255, blank=True)
    next_url = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return '{interval} {amount_presets}'.format(
            interval=self.interval,
            amount_presets=self.amount_presets
        )

    def make_form(self, **kwargs):
        from .forms import DonationSettingsForm

        reference = kwargs.pop('reference', '')

        form = DonationSettingsForm(
            data={
                'title': self.title,
                'interval': self.interval,
                'amount_presets': self.amount_presets,
                'initial_amount': self.initial_amount,
                'initial_interval': self.initial_interval,
                'reference': self.reference or reference,
                'purpose': self.purpose,
            }
        )
        return form.make_donation_form(**kwargs)
