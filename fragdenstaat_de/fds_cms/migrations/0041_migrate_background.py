from django.db import migrations


def migrate_background(apps, schema_editor):
    CardInnerCMSPlugin = apps.get_model("fds_cms", "CardInnerCMSPlugin")
    CardCMSPlugin = apps.get_model("fds_cms", "CardCMSPlugin")

    for inner in CardInnerCMSPlugin.objects.all():
        if inner.background:
            parent = inner.parent
            card = CardCMSPlugin.objects.get(cmsplugin_ptr=parent)
            card.background = inner.background
            card.save()


class Migration(migrations.Migration):
    dependencies = [
        ("fds_cms", "0040_cardcmsplugin_background"),
    ]

    operations = [
        migrations.RunPython(migrate_background, atomic=False),
    ]
