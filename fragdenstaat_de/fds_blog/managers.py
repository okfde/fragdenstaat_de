from django.db import models
from django.utils import timezone
from django.contrib.sites.models import Site

from parler.managers import TranslatableManager

DRAFT = 0
HIDDEN = 1
PUBLISHED = 2


def articles_published(queryset):
    """
    Return only the entries published.
    """
    now = timezone.now()
    return queryset.filter(
        models.Q(start_publication__lte=now) |
        models.Q(start_publication=None),
        models.Q(end_publication__gt=now) |
        models.Q(end_publication=None),
        status=PUBLISHED, sites=Site.objects.get_current())


def articles_visible(queryset):
    """
    Return only the entries published.
    """
    now = timezone.now()
    return queryset.filter(
        models.Q(start_publication__lte=now) |
        models.Q(start_publication=None),
        models.Q(end_publication__gt=now) |
        models.Q(end_publication=None),
        models.Q(status=PUBLISHED) | models.Q(status=HIDDEN),
        sites=Site.objects.get_current()
    )


class CategoryManager(TranslatableManager):
    pass


class ArticlePublishedManager(models.Manager):
    """
    Manager to retrieve published entries.
    """

    def get_queryset(self):
        """
        Return published entries.
        """
        return articles_published(
            super(ArticlePublishedManager, self).get_queryset())

    def on_site(self):
        """
        Return entries published on current site.
        """
        return super(ArticlePublishedManager, self).get_queryset().filter(
            sites=Site.objects.get_current())

    def search(self, pattern):
        """
        Basic search on entries.
        """
        lookup = None
        for pattern in pattern.split():
            query_part = models.Q()
            for field in ('title', 'content'):
                query_part |= models.Q(**{'%s__icontains' % field: pattern})
            if lookup is None:
                lookup = query_part
            else:
                lookup |= query_part

        return self.get_queryset().filter(lookup)


class RelatedPublishedManager(models.Manager):
    """
    Manager to retrieve objects associated with published entries.
    """

    def get_queryset(self):
        """
        Return a queryset containing published entries.
        """
        now = timezone.now()
        return super(
            RelatedPublishedManager, self).get_queryset().filter(
            models.Q(articles__start_publication__lte=now) |
            models.Q(articles__start_publication=None),
            models.Q(articles__end_publication__gt=now) |
            models.Q(articles__end_publication=None),
            articles__status=PUBLISHED,
            articles__sites=Site.objects.get_current()
            ).distinct()
