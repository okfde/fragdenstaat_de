from django.db import migrations


def migrate_background(apps, schema_editor):
    CardCMSInnerPlugin = apps.get_model("fds_cms", "CardInnerCMSPlugin")

    for inner in CardCMSInnerPlugin.objects.all():
        if inner.background:
            card = inner.parent
            card.background = inner.background
            card.save()


class Migration(migrations.Migration):

    dependencies = [
        ("fds_cms", "0040_cardcmsplugin_background"),
    ]

    operations = [
        migrations.RunPython(migrate_background, atomic=False),
    ]
