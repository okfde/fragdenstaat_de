# Generated by Django 4.2.14 on 2024-07-29 12:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fds_donation", "0044_donationformcmsplugin_open_in_new_tab"),
    ]

    operations = [
        migrations.AddField(
            model_name="donationprogressbarcmsplugin",
            name="purpose",
            field=models.CharField(blank=True),
        ),
    ]