# Generated by Django 3.2.11 on 2022-01-17 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fds_cms', '0034_cardcmsplugin'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cardimagecmsplugin',
            name='overlap',
            field=models.CharField(choices=[('left', 'Left'), ('right', 'Right'), ('center', 'Center')], default='right', max_length=10, verbose_name='Overlap'),
        ),
    ]