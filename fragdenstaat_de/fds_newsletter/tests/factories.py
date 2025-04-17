from django.utils import timezone

import factory
from factory.django import DjangoModelFactory

from ..models import Newsletter, Subscriber


class NewsletterFactory(DjangoModelFactory):
    class Meta:
        model = Newsletter

    title = factory.Sequence(lambda n: "Newsletter %s" % n)


class SubscriberFactory(DjangoModelFactory):
    class Meta:
        model = Subscriber

    newsletter = factory.SubFactory(NewsletterFactory)
    email = factory.Sequence(lambda n: "email_%s@example.com" % n)
    subscribed = factory.LazyAttribute(lambda: timezone.now())
