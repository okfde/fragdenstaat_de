# Generated by Django 4.2.4 on 2024-04-19 14:47

import django.utils.timezone
from django.db import migrations, models


def migrate_start_creation(apps, schema_editor):
    Article = apps.get_model("fds_blog", "Article")

    for article in Article.objects.filter(start_publication__isnull=True):
        article.start_publication = article.creation_date
        article.save()


class Migration(migrations.Migration):
    dependencies = [
        ("fds_blog", "0015_alter_article_unique_together_alter_article_audio_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_start_creation),
        migrations.AlterField(
            model_name="article",
            name="start_publication",
            field=models.DateTimeField(
                db_index=True,
                default=django.utils.timezone.now,
                help_text="Start date of publication. Used to build the entry's URL.",
                verbose_name="start publication",
            ),
        ),
    ]