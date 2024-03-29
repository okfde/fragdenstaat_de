# Generated by Django 2.2.4 on 2019-09-27 10:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("cms", "0022_auto_20180620_1551"),
    ]

    operations = [
        migrations.CreateModel(
            name="DonationGift",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("category_slug", models.SlugField(blank=True, max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="DonationGiftFormCMSPlugin",
            fields=[
                (
                    "cmsplugin_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        related_name="fds_donation_donationgiftformcmsplugin",
                        serialize=False,
                        to="cms.CMSPlugin",
                    ),
                ),
                ("category", models.SlugField()),
            ],
            options={
                "abstract": False,
            },
            bases=("cms.cmsplugin",),
        ),
    ]
