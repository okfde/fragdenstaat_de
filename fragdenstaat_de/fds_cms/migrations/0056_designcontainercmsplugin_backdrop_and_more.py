# Generated by Django 4.1.4 on 2023-02-20 15:21

import django.db.models.deletion
from django.db import migrations, models

mapping = (
    ("blue-600", "blue-600"),
    ("blue", "blue-10"),
    ("gray-100", "gray-100"),
    ("gray", "gray-200"),
    ("yellow-200", "yellow-200"),
    ("yellow", "yellow-100"),
)


def extract_backdrop(apps, schema_editor):
    DesignContainer = apps.get_model("fds_cms", "DesignContainerCMSPlugin")

    containers = DesignContainer.objects.filter(extra_classes__contains="backdrop")
    for container in containers:
        classes = container.extra_classes.split(" ")
        backdrop_classes = list(filter(lambda c: "backdrop" in c, classes))

        container.background = ""

        for keyword, color in mapping:
            if keyword in backdrop_classes[0]:
                container.background = color
                break

        if "backdrop-75" in classes:
            container.backdrop = "75"
        else:
            container.backdrop = "50"

        container.extra_classes = " ".join(set(classes) - set(backdrop_classes))

        container.save()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0022_auto_20180620_1551"),
        ("fds_cms", "0055_auto_20221125_1134"),
    ]

    operations = [
        migrations.AddField(
            model_name="designcontainercmsplugin",
            name="backdrop",
            field=models.CharField(
                choices=[("", "None"), ("50", "50 %"), ("75", "75 %")],
                default="",
                max_length=5,
                verbose_name="Backdrop",
            ),
        ),
        migrations.RunPython(extract_backdrop),
    ]
