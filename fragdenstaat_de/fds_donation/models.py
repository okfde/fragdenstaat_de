from django.db import models

from cms.models.pluginmodel import CMSPlugin


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

    def __str__(self):
        return str(self.category)
