# Generated by Django 3.0.5 on 2020-05-22 16:29

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fds_donation", "0018_auto_20200420_1703"),
    ]

    operations = [
        migrations.AddField(
            model_name="donor",
            name="recurring",
            field=models.BooleanField(default=False),
        ),
    ]
