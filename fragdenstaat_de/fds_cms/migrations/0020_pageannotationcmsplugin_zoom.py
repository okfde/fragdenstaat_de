# Generated by Django 2.2.4 on 2020-02-18 10:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fds_cms", "0019_auto_20191206_1334"),
    ]

    operations = [
        migrations.AddField(
            model_name="pageannotationcmsplugin",
            name="zoom",
            field=models.BooleanField(default=True),
        ),
    ]
