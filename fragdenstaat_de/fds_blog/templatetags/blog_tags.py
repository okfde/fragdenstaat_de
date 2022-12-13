from django import template

from ..managers import articles_published
from ..models import Article

register = template.Library()


@register.filter
def get_next_read(article):
    qs = articles_published(Article.objects.filter(language=article.language))
    if article.start_publication:
        return qs.filter(start_publication__lt=article.start_publication).first()
    return qs.exclude(pk=article.pk).first()
