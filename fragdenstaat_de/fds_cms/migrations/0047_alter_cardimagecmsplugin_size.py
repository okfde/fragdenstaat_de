# Generated by Django 3.2.12 on 2022-05-04 08:35

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fds_cms", "0046_revealmorecmsplugin"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cardimagecmsplugin",
            name="size",
            field=models.CharField(
                choices=[("sm", "Small"), ("lg", "Large"), ("lg-wide", "Large (wide)")],
                default="lg",
                max_length=10,
                verbose_name="Size",
            ),
        ),
    ]
