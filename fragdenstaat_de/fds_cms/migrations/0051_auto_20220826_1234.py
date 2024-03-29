# Generated by Django 3.2.14 on 2022-08-26 10:34
from django.db import migrations


def combine_names(apps, schema_editor):
    CMSPlugin = apps.get_model("cms", "CMSPlugin")
    old_names = [
        "CardPlugin",
        "CardHeaderPlugin",
        "CardInnerPlugin",
        "CardImagePlugin",
        "CardIconPlugin",
        "CardLinkPlugin",
    ]
    new_prefix = "Fds"
    for old_name in old_names:
        CMSPlugin.objects.filter(plugin_type=old_name).update(
            plugin_type=new_prefix + old_name
        )


class Migration(migrations.Migration):
    dependencies = [
        ("fds_cms", "0050_alter_vegachartcmsplugin_title"),
    ]

    operations = [
        migrations.RunPython(combine_names),
    ]
