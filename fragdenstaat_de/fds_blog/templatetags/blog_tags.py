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


@register.inclusion_tag("fds_blog/blog_preview.html", takes_context=True)
def get_blog_preview(context, amount=6):
    amount = min(int(amount), 20)
    articles = Article.published.all()[:amount]

    return {"articles": articles, "request": context.get("request")}
