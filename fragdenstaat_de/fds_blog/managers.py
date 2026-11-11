from django.db import models
from django.utils import timezone

from parler.managers import TranslatableManager

DRAFT = 0
HIDDEN = 1
PUBLISHED = 2


def articles_published(queryset, site=None):
    """
    Return only the entries published.
    """
    now = timezone.now()
    filter_kwargs = {}
    if site is not None:
        filter_kwargs = {"sites": site}
    return queryset.filter(
        models.Q(start_publication__lte=now) | models.Q(start_publication=None),
        models.Q(end_publication__gt=now) | models.Q(end_publication=None),
        status=PUBLISHED,
        **filter_kwargs,
    )


def articles_visible(queryset, site=None):
    """
    Return only the entries published.
    """
    now = timezone.now()
    filter_kwargs = {}
    if site is not None:
        filter_kwargs = {"sites": site}
    return queryset.filter(
        models.Q(start_publication__lte=now) | models.Q(start_publication=None),
        models.Q(end_publication__gt=now) | models.Q(end_publication=None),
        models.Q(status=PUBLISHED) | models.Q(status=HIDDEN),
        **filter_kwargs,
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
        qs = super().get_queryset()
        return articles_published(qs)

    def on_site(self, site):
        """
        Return entries published on current site.
        """
        return self.get_queryset().filter(sites=site)

    def search(self, pattern):
        """
        Basic search on entries.
        """
        lookup = None
        for part in pattern.split():
            query_part = models.Q()
            for field in ("title", "content"):
                query_part |= models.Q(**{"%s__icontains" % field: part})
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
        return (
            super(RelatedPublishedManager, self)
            .get_queryset()
            .filter(
                models.Q(articles__start_publication__lte=now)
                | models.Q(articles__start_publication=None),
                models.Q(articles__end_publication__gt=now)
                | models.Q(articles__end_publication=None),
                articles__status=PUBLISHED,
            )
            .distinct()
        )
