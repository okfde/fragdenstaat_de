# Generated by Django 4.2.4 on 2024-07-18 14:52

from django.db import migrations, models


def migrate_featured_options(apps, schema_editor):
    LatestArticlesPlugin = apps.get_model("fds_blog", "LatestArticlesPlugin")

    LatestArticlesPlugin.objects.filter(featured="false").update(featured="show")
    LatestArticlesPlugin.objects.filter(featured="true").update(featured="hide")


class Migration(migrations.Migration):
    dependencies = [
        ("fds_blog", "0022_alter_articlepreviewplugin_template_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="latestarticlesplugin",
            name="featured",
            field=models.CharField(
                blank=True,
                choices=[
                    ("show", "Show featured articles only"),
                    ("hide", "Hide featured articles"),
                    ("one", "Only show one featured article"),
                ],
                max_length=5,
                null=True,
                verbose_name="featured",
            ),
        ),
        migrations.RunPython(migrate_featured_options, migrations.RunPython.noop),
    ]
