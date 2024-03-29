# Generated by Django 3.1.4 on 2021-01-11 19:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fds_donation", "0030_donationprogressbarcmsplugin_reached_goal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="donation",
            name="identifier",
            field=models.CharField(blank=True, max_length=1024),
        ),
        migrations.AlterField(
            model_name="donortag",
            name="name",
            field=models.CharField(max_length=100, unique=True, verbose_name="name"),
        ),
        migrations.AlterField(
            model_name="donortag",
            name="slug",
            field=models.SlugField(max_length=100, unique=True, verbose_name="slug"),
        ),
    ]
