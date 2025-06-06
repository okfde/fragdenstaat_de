# Generated by Django 4.2.16 on 2025-04-15 13:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0035_auto_20230822_2208_squashed_0036_auto_20240311_1028"),
        ("fds_cms", "0074_pagepreviewcmsplugin"),
    ]

    operations = [
        migrations.CreateModel(
            name="OpenSearchCMSPlugin",
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
                ("search_endpoint", models.URLField()),
            ],
            bases=("cms.cmsplugin",),
        ),
    ]
