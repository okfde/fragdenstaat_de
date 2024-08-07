# Generated by Django 4.2.4 on 2024-04-18 21:20

import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
from django.db import migrations, models

import filer.fields.file


class Migration(migrations.Migration):
    dependencies = [
        ("filer", "0015_alter_file_owner_alter_file_polymorphic_ctype_and_more"),
        ("fds_blog", "0014_article_audio_article_audio_duration"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="article",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="article",
            name="audio",
            field=filer.fields.file.FilerFileField(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="audio_articles",
                to="filer.file",
                verbose_name="audio file",
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="creation_date",
            field=models.DateTimeField(
                db_index=True,
                default=django.utils.timezone.now,
                verbose_name="creation date",
            ),
        ),
        migrations.AlterField(
            model_name="article",
            name="start_publication",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Start date of publication. Used to build the entry's URL.",
                null=True,
                verbose_name="start publication",
            ),
        ),
        migrations.AddConstraint(
            model_name="article",
            constraint=models.UniqueConstraint(
                models.F("slug"),
                django.db.models.functions.datetime.Extract(
                    "start_publication", "year"
                ),
                django.db.models.functions.datetime.Extract(
                    "start_publication", "month"
                ),
                name="unique_blog_url",
            ),
        ),
    ]
