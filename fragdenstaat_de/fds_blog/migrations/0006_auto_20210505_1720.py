# Generated by Django 3.1.8 on 2021-05-05 15:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fds_blog", "0005_auto_20191001_1644"),
    ]

    operations = [
        migrations.AlterField(
            model_name="article",
            name="content_template",
            field=models.CharField(
                choices=[
                    ("fds_blog/_article_detail.html", "Default template"),
                    ("fds_blog/content/_article_no_image.html", "No image in article"),
                ],
                default="fds_blog/_article_detail.html",
                help_text="Template used to display the article's content.",
                max_length=250,
                verbose_name="content template",
            ),
        ),
        migrations.AlterField(
            model_name="articletag",
            name="name",
            field=models.CharField(max_length=100, unique=True, verbose_name="name"),
        ),
        migrations.AlterField(
            model_name="articletag",
            name="slug",
            field=models.SlugField(max_length=100, unique=True, verbose_name="slug"),
        ),
        migrations.AlterField(
            model_name="latestarticlesplugin",
            name="featured",
            field=models.BooleanField(
                blank=True,
                choices=[
                    (True, "Show featured articles only"),
                    (False, "Hide featured articles"),
                ],
                null=True,
                verbose_name="featured",
            ),
        ),
        migrations.AlterField(
            model_name="latestarticlesplugin",
            name="template",
            field=models.CharField(
                blank=True,
                choices=[
                    ("fds_blog/plugins/latest_articles.html", "Normal"),
                    ("fds_blog/plugins/featured_articles.html", "Featured"),
                    ("fds_blog/plugins/simple_articles.html", "Simple"),
                    ("fds_blog/plugins/slider_articles.html", "Featured Slider"),
                ],
                help_text="template used to display the plugin",
                max_length=250,
                verbose_name="template",
            ),
        ),
    ]
