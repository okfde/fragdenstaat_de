# Generated by Django 2.2.4 on 2020-02-03 16:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fds_newsletter', '0004_auto_20191030_1601'),
    ]

    operations = [
        migrations.CreateModel(
            name='MailingSubscription',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('newsletter.subscription',),
        ),
    ]
