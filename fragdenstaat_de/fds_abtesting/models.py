from unicodedata import name

from django.db import models


class ABTest(models.Model):
    name = models.CharField(max_length=500)
    action = models.CharField(max_length=500)

    def __str__(self):
        return name
