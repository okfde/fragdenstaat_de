from django.db import migrations, models


def migrate_background(apps, schema_editor):
    from fragdenstaat_de.fds_cms.models import CardCMSPlugin

    # can't use apps.get_models as model methods are missing there

    for card in CardCMSPlugin.objects.all():
        inner = card.get_children().filter(plugin_type="CardInnerPlugin").first()

        if inner:
            (instance, plugin) = inner.get_plugin_instance()
            card.background = instance.background
            card.save()


class Migration(migrations.Migration):

    dependencies = [
        ("fds_cms", "0040_cardcmsplugin_background"),
    ]

    operations = [
        migrations.RunPython(migrate_background, atomic=False),
    ]
