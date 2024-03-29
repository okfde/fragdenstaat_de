# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-06-05 08:53
from __future__ import unicode_literals

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import cms.models.fields
import filer.fields.image


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.FILER_IMAGE_MODEL),
        ("cms", "0020_old_tree_cleanup"),
        ("fds_cms", "0003_documentpagescmsplugin_title"),
    ]

    operations = [
        migrations.CreateModel(
            name="PrimaryLinkCMSPlugin",
            fields=[
                (
                    "cmsplugin_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        related_name="fds_cms_primarylinkcmsplugin",
                        serialize=False,
                        to="cms.CMSPlugin",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "url",
                    models.CharField(
                        blank=True,
                        help_text="if present image will be clickable",
                        max_length=255,
                        null=True,
                        verbose_name="link",
                    ),
                ),
                (
                    "anchor",
                    models.CharField(
                        blank=True,
                        help_text="Page anchor.",
                        max_length=128,
                        verbose_name="anchor",
                    ),
                ),
                (
                    "template",
                    models.CharField(
                        blank=True,
                        choices=[("", "Default template")],
                        default="",
                        max_length=50,
                        verbose_name="Template",
                    ),
                ),
                (
                    "image",
                    filer.fields.image.FilerImageField(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.FILER_IMAGE_MODEL,
                        verbose_name="image",
                    ),
                ),
                (
                    "page_link",
                    cms.models.fields.PageField(
                        blank=True,
                        help_text="if present image will be clickable",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="cms.Page",
                        verbose_name="page link",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("cms.cmsplugin",),
        ),
    ]
