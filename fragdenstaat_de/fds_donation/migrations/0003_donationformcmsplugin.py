# Generated by Django 2.2.4 on 2019-10-18 16:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0022_auto_20180620_1551"),
        ("fds_donation", "0002_auto_20190927_1605"),
    ]

    operations = [
        migrations.CreateModel(
            name="DonationFormCMSPlugin",
            fields=[
                (
                    "cmsplugin_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        related_name="fds_donation_donationformcmsplugin",
                        serialize=False,
                        to="cms.CMSPlugin",
                    ),
                ),
                (
                    "interval",
                    models.CharField(
                        choices=[
                            ("once", "Only once"),
                            ("recurring", "Only recurring"),
                            ("once_recurring", "Both"),
                        ],
                        max_length=20,
                    ),
                ),
                ("amount_presets", models.CharField(blank=True, max_length=255)),
                ("initial_amount", models.IntegerField(blank=True, null=True)),
                ("initial_interval", models.IntegerField(null=True)),
                ("reference", models.SlugField(blank=True)),
                ("form_action", models.CharField(blank=True, max_length=255)),
                ("next_url", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "abstract": False,
            },
            bases=("cms.cmsplugin",),
        ),
    ]
