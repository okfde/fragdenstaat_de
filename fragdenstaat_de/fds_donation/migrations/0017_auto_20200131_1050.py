# Generated by Django 2.2.4 on 2020-01-31 09:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fds_donation", "0016_donation_receipt_date"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="donation",
            name="receipt_given",
        ),
        migrations.AddField(
            model_name="donation",
            name="export_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
