from django.db import models

from cms.models.pluginmodel import CMSPlugin


class ABTest(models.Model):
    name = models.CharField(max_length=500)
    action = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class ABTestEvent(models.Model):
    ab_test = models.ForeignKey(ABTest, on_delete=models.CASCADE)
    variant = models.CharField(max_length=500)


class ABTestVariant(CMSPlugin):
    name = models.CharField(max_length=500)
    action_text = models.CharField(max_length=500)
    action_class = models.CharField(max_length=500, blank=True)


class ABTestCMSPlugin(CMSPlugin):
    ab_test = models.ForeignKey(ABTest, on_delete=models.CASCADE)
