# Generated by Django 3.2.14 on 2022-09-06 11:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [('fds_blog', '0009_infotextboxcmsplugin'), ('fds_blog', '0010_auto_20220901_1900'), ('fds_blog', '0011_infotextboxcmsplugin'), ('fds_blog', '0012_remove_infotextboxcmsplugin_background')]

    dependencies = [
        ('fds_blog', '0008_article_kicker'),
        ('cms', '0022_auto_20180620_1551'),
    ]

    operations = [
        migrations.CreateModel(
            name='DetailsBoxCMSPlugin',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='fds_blog_detailsboxcmsplugin', serialize=False, to='cms.cmsplugin')),
                ('title', models.CharField(blank=True, max_length=100)),
                ('content', models.TextField(blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
        migrations.CreateModel(
            name='InfotextboxCMSPlugin',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='fds_blog_infotextboxcmsplugin', serialize=False, to='cms.cmsplugin')),
                ('content', models.TextField(blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
    ]