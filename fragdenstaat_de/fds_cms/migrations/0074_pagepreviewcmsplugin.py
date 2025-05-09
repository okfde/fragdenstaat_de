# Generated by Django 4.2.16 on 2025-03-10 13:42

import cms.models.fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0035_auto_20230822_2208_squashed_0036_auto_20240311_1028"),
        migrations.swappable_dependency(settings.FILER_IMAGE_MODEL),
        ("fds_cms", "0073_remove_documentcollectionembedcmsplugin_settings_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PagePreviewCMSPlugin",
            fields=[
                (
                    "cmsplugin_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        related_name="%(app_label)s_%(class)s",
                        serialize=False,
                        to="cms.cmsplugin",
                    ),
                ),
                (
                    "page",
                    cms.models.fields.PageField(
                        on_delete=django.db.models.deletion.CASCADE, to="cms.page"
                    ),
                ),
            ],
            bases=("cms.cmsplugin",),
        ),
    ]
