# -*- encoding: utf-8 -*-
from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify
from django.utils import translation


class Command(BaseCommand):
    help = "Loads Berlin"
    topic_cache = {}

    def handle(self, filepath, *args, **options):
        from django.contrib.auth.models import User
        from django.contrib.sites.models import Site

        from froide.publicbody.models import (
            FoiLaw,
            Jurisdiction,
            PublicBody,
            PublicBodyTopic,
        )

        translation.activate(settings.LANGUAGE_CODE)

        sw = User.objects.get(username="sw")
        site = Site.objects.get_current()
        self.topic_cache = {pb.slug: pb for pb in PublicBodyTopic.objects.all()}
        juris = Jurisdiction.objects.get(slug="berlin")

        laws = FoiLaw.objects.filter(jurisdiction=juris)

        # importing Berlin
        with open(filepath) as f:
            first = True
            for line in f:
                if first:
                    first = False
                    continue
                line = line.decode("utf-8")
                href, rest = line.split(",", 1)
                name, email = rest.rsplit(",", 1)
                if name.startswith('"') and name.endswith('"'):
                    name = name[1:-1]
                if not href:
                    href = None
                if not email:
                    email = None
                topic = self.get_topic(name)
                classification = self.get_classification(name)
                try:
                    PublicBody.objects.get(slug=slugify(name))
                    continue
                except PublicBody.DoesNotExist:
                    pass
                self.stdout.write(("Trying: %s\n" % name).encode("utf-8"))
                public_body = PublicBody.objects.create(
                    name=name,
                    slug=slugify(name),
                    topic=topic,
                    description="",
                    url=href,
                    classification=classification,
                    classification_slug=slugify(classification),
                    email=email,
                    contact="",
                    address="",
                    website_dump="",
                    request_note="",
                    _created_by=sw,
                    _updated_by=sw,
                    confirmed=True,
                    site=site,
                    jurisdiction=juris,
                )
                public_body.laws.add(*laws)
                self.stdout.write(("%s\n" % public_body).encode("utf-8"))

    def get_classification(self, name):
        mapping = ["Gericht", "Stiftung", "Kammer", "Hochschule", "Universität"]
        for m in mapping:
            if m.lower() in name.lower():
                return m
        classifications = name.split()
        if classifications[0].startswith(
            (
                "Berliner",
                "Der",
                "Die",
                "Das",
                "Deutsche",
            )
        ):
            classification = classifications[1]
        elif classifications[0].startswith(
            (
                "Zentrale",
                "Staatl",
            )
        ):
            classification = " ".join(classifications[:2])
        elif classifications[0].endswith("-"):
            classification = " ".join(classifications[:3])
        else:
            classification = classifications[0]
        return classification

    def get_topic(self, name):
        name = name.lower()
        mapping = {
            "gericht": "justiz",
            "polizei": "inneres",
            "schul": "bildung-und-forschung",
            "rechnungs": "finanzen",
            "staatsanwaltschaft": "justiz",
            "liegenschaftsbetrieb": "verkehr-und-bau",
            "hrungshilfe": "justiz",
            "finanzamt": "finanzen",
            "hrungsaufsichtsstelle": "justiz",
            "landwirtschaftskammer": "landwirtschaft-und-verbraucherschutz",
            "jugendarrestanstalt": "justiz",
            "justiz": "justiz",
            "umwelt": "umwelt",
            "straßenbau": "verkehr-und-bau",
            "wald": "umwelt",
            "kriminal": "inneres",
            "prüfungsamt": "bildung-und-forschung",
        }
        for k, v in mapping.items():
            if k in name:
                return self.topic_cache[v]
        return self.topic_cache["andere"]
