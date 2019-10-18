from django.db import models
from django.utils.translation import ugettext_lazy as _

from cms.models.pluginmodel import CMSPlugin


INTERVAL_SETTINGS_CHOICES = [
    ('once', _('Only once')),
    ('recurring', _('Only recurring')),
    ('once_recurring', _('Both')),
]


class DonationGift(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category_slug = models.SlugField(max_length=255, blank=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class DonationGiftFormCMSPlugin(CMSPlugin):
    category = models.SlugField()
    next_url = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return str(self.category)


class DonationFormCMSPlugin(CMSPlugin):
    interval = models.CharField(
        max_length=20, choices=INTERVAL_SETTINGS_CHOICES
    )
    amount_presets = models.CharField(max_length=255, blank=True)
    initial_amount = models.IntegerField(null=True, blank=True)
    initial_interval = models.IntegerField(null=True, blank=True)

    reference = models.SlugField(blank=True)

    form_action = models.CharField(max_length=255, blank=True)
    next_url = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return '{interval} {amount_presets}'.format(
            interval=self.interval,
            amount_presets=self.amount_presets
        )

    def make_form(self, **kwargs):
        from .forms import DonationSettingsForm

        form = DonationSettingsForm(
            data={
                'interval': self.interval,
                'amount_presets': self.amount_presets,
                'initial_amount': self.initial_amount,
                'initial_interval': self.initial_amount,
                'reference': self.reference,
            }
        )
        return form.make_donation_form(**kwargs)
