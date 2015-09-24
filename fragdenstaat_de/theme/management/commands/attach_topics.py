# -*- encoding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils import translation
from django.conf import settings


class Command(BaseCommand):
    help = "Attach topic to jurisdiction's public bodies"
    topic_cache = {}

    def add_arguments(self, parser):
        parser.add_argument('jurisdiction')

    def handle(self, *args, **options):

        from froide.publicbody.models import (PublicBodyTag, PublicBody,
            Jurisdiction)

        translation.activate(settings.LANGUAGE_CODE)

        jurisdiction_slug = options.get('jurisdiction')
        self.topic_cache = dict([(tag.slug, tag) for tag in PublicBodyTag.objects.filter(is_topic=True)])
        juris = Jurisdiction.objects.get(slug=jurisdiction_slug)

        for pb in PublicBody.objects.filter(jurisdiction=juris):
            topic = self.get_topic(pb)
            if topic is not None:
                pb.tags.add(topic)

    def get_topic(self, pb):
        name = pb.name.lower()
        mapping = {
            'polizei': 'inneres',
            'kriminal': 'inneres',

            'schul': 'bildung-und-forschung',
            'univ': 'bildung-und-forschung',
            'student': 'bildung-und-forschung',
            'schul': 'bildung-und-forschung',

            'rechnungs': 'finanzen',
            'finanz': 'finanzen',

            'arbeit': 'arbeit-und-soziales',
            'job': 'arbeit-und-soziales',

            'staatsanwaltschaft': 'justiz',
            'justiz': 'justiz',
            'gericht': 'justiz',
            'vollzug': 'justiz',

            'kammer': 'wirtschaft',

            'bauamt': 'bau',

            'umwelt': 'umwelt',
            'wald': 'umwelt',
        }
        for k, v in mapping.items():
            if k in name:
                return self.topic_cache[v]
        return None
