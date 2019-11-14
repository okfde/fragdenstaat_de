from django import template

from ..models import Article
from ..managers import articles_published

register = template.Library()


@register.filter
def get_next_read(article):

    qs = articles_published(Article.objects.all())
    if article.start_publication:
        try:
            return qs.filter(start_publication__lt=article.start_publication)[0]
        except IndexError:
            pass
    return qs.exclude(pk=article.pk)[0]
