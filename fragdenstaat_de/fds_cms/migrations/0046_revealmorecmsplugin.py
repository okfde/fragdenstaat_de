# Generated by Django 3.2.12 on 2022-03-10 17:55

import django.db.models.deletion
from django.db import migrations, models

import djangocms_bootstrap4.fields


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0022_auto_20180620_1551"),
        ("fds_cms", "0045_auto_20220310_1523"),
    ]

    operations = [
        migrations.CreateModel(
            name="RevealMoreCMSPlugin",
            fields=[
                (
                    "cmsplugin_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        related_name="fds_cms_revealmorecmsplugin",
                        serialize=False,
                        to="cms.cmsplugin",
                    ),
                ),
                (
                    "cutoff",
                    models.PositiveIntegerField(default=1, verbose_name="Cutoff after"),
                ),
                (
                    "unit",
                    models.CharField(
                        choices=[
                            ("rows", "grid rows"),
                            ("rem", "Line heights"),
                            ("%", "percent"),
                        ],
                        max_length=10,
                        verbose_name="Unit",
                    ),
                ),
                (
                    "color",
                    models.CharField(
                        choices=[
                            ("", "None"),
                            ("primary", "Primary"),
                            ("secondary", "Secondary"),
                            ("info", "Info"),
                            ("light", "Light"),
                            ("dark", "Dark"),
                            ("success", "Success"),
                            ("warning", "Warning"),
                            ("danger", "Danger"),
                            ("purple", "Purple"),
                            ("pink", "Pink"),
                            ("yellow", "Yellow"),
                            ("cyan", "Cyan"),
                            ("gray", "Gray"),
                            ("gray-dark", "Gray Dark"),
                            ("white", "White"),
                            ("gray-100", "Gray 100"),
                            ("gray-200", "Gray 200"),
                            ("gray-300", "Gray 300"),
                            ("gray-400", "Gray 400"),
                            ("gray-500", "Gray 500"),
                            ("gray-600", "Gray 600"),
                            ("gray-700", "Gray 700"),
                            ("gray-800", "Gray 800"),
                            ("gray-900", "Gray 900"),
                            ("blue-10", "Blue 10"),
                            ("blue-20", "Blue 20"),
                            ("blue-30", "Blue 30"),
                            ("blue-100", "Blue 100"),
                            ("blue-200", "Blue 200"),
                            ("blue-300", "Blue 300"),
                            ("blue-400", "Blue 400"),
                            ("blue-500", "Blue 500"),
                            ("blue-600", "Blue 600"),
                            ("blue-700", "Blue 700"),
                            ("blue-800", "Blue 800"),
                            ("yellow-100", "Yellow 100"),
                            ("yellow-200", "Yellow 200"),
                            ("yellow-300", "Yellow 300"),
                        ],
                        max_length=50,
                        verbose_name="Overlay color",
                    ),
                ),
                (
                    "reveal_text",
                    models.CharField(
                        blank=True, max_length=50, verbose_name="Reveal text"
                    ),
                ),
                (
                    "attributes",
                    djangocms_bootstrap4.fields.AttributesField(
                        blank=True, default=dict, verbose_name="Attributes"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("cms.cmsplugin",),
        ),
    ]