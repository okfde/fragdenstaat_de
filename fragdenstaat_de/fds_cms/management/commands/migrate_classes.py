from django.core.management.base import BaseCommand
from django.db.models import F, Value
from django.db.models.functions import Replace

from djangocms_frontend.models import FrontendUIItem
from djangocms_text.models import Text
from froide_govplan.models import GovernmentPlansCMSPlugin

from fragdenstaat_de.fds_cms.models import (
    CollapsibleCMSPlugin,
    DesignContainerCMSPlugin,
    PrimaryLinkCMSPlugin,
    SliderCMSPlugin,
)
from fragdenstaat_de.fds_donation.models import DonationFormCMSPlugin


class Command(BaseCommand):
    help = "Migrate CSS classes in CMS"

    def add_arguments(self, parser):
        parser.add_argument("old_class", help="Old class name to migrate")
        parser.add_argument("new_class", help="New class name to migrate to")
        parser.add_argument(
            "--dry-run", action="store_true", help="Run without making changes"
        )

    def handle(self, **options):
        old_class = options["old_class"]
        new_class = options["new_class"]
        dry_run = options["dry_run"]

        extra_classes = [
            PrimaryLinkCMSPlugin,
            DesignContainerCMSPlugin,
            CollapsibleCMSPlugin,
            SliderCMSPlugin,
            DonationFormCMSPlugin,
            GovernmentPlansCMSPlugin,
        ]

        def log(model, instance, old, new):
            if dry_run:
                self.stdout.write(
                    f"Would update {model} {instance.pk} from `{old}` to `{new}`"
                )
            else:
                self.stdout.write(
                    f"Updating {model} {instance.pk} from `{old}` to `{new}`"
                )

        # TODO: refactor once Django has better support for updating JSON fields
        instances = FrontendUIItem.objects.filter(
            config__attributes__class__icontains=old_class
        )
        for instance in instances:
            current = instance.config["attributes"]["class"]
            changed = current.replace(old_class, new_class)

            log(instance.plugin_type, instance, current, changed)

            if not dry_run:
                instance.config["attributes"]["class"] = changed
                instance.save()

        for Model in extra_classes:
            instances = Model.objects.filter(
                extra_classes__icontains=old_class
            ).annotate(
                new_extra_classes=Replace(
                    "extra_classes", Value(old_class), Value(new_class)
                )
            )

            for instance in instances:
                log(
                    Model.__name__,
                    instance,
                    instance.extra_classes,
                    instance.new_extra_classes,
                )

            if not dry_run:
                instances.update(extra_classes=F("new_extra_classes"))

        text_instances = Text.objects.filter(body__icontains=old_class)
        if text_instances.exists():
            self.stdout.write(
                f"Warning: Found old classes in {text_instances.count()} text plugin(s). Please check them manually."
            )
