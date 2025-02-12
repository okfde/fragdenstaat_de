from django.apps import apps
from django.core.management.commands.makemigrations import Command as OriginalCommand


class Command(OriginalCommand):
    def add_arguments(self, parser):
        parser.add_argument("--ignore-app", nargs="+")
        return super().add_arguments(parser)

    def handle(self, *app_labels, **options):
        if app_labels or not options["check_changes"]:
            return super().handle(*app_labels, **options)

        app_labels = {cfg.label for cfg in apps.get_app_configs()} - set(
            options["ignore_app"]
        )
        return super().handle(*app_labels, **options)
