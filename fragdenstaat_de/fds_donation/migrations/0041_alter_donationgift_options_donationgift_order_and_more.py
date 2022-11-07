# Generated by Django 4.0.7 on 2022-09-27 11:56

from django.db import migrations, models


def reorder(apps, schema_editor):
    DonationGift = apps.get_model("fds_donation", "DonationGift")
    for order, item in enumerate(DonationGift.objects.all(), 1):
        item.order = order
        item.save(update_fields=["order"])


class Migration(migrations.Migration):

    dependencies = [
        ("fds_donation", "0040_donationgiftorder"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="donationgift",
            options={
                "ordering": ("order", "name"),
                "verbose_name": "donation gift",
                "verbose_name_plural": "donation gifts",
            },
        ),
        migrations.AddField(
            model_name="donationgift",
            name="order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="donortag",
            name="slug",
            field=models.SlugField(
                allow_unicode=True, max_length=100, unique=True, verbose_name="slug"
            ),
        ),
        migrations.RunPython(reorder, reverse_code=migrations.RunPython.noop),
    ]