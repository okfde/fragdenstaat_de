# Generated by Django 4.2.14 on 2024-08-29 14:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djangocms_alias", "0004_alter_aliascontent_language"),
        ("fds_blog", "0023_alter_latestarticlesplugin_featured"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="donation_banner",
            field=models.ForeignKey(
                blank=True,
                default=None,
                help_text="Inserted after a couple of paragraphs on the article page.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="donation_banner",
                to="djangocms_alias.alias",
                verbose_name="Donation banner",
            ),
        ),
    ]
