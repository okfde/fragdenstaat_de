# Generated by Django 4.2.16 on 2025-02-24 16:31

from django.conf import settings
from django.db import migrations
import django.db.models.deletion
import filer.fields.image


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.FILER_IMAGE_MODEL),
        ("fds_events", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="image",
            field=filer.fields.image.FilerImageField(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.FILER_IMAGE_MODEL,
                verbose_name="image",
            ),
        ),
    ]
