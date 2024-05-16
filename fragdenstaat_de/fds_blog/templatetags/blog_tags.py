from typing import Tuple

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


@register.filter
def split_for_banner(content: str) -> Tuple[str, str]:
    # splits the content into content that is shown before the ad, and content that is shown after the ad
    TAG = "<h3"

    sections = content.split(TAG)

    # if there are at least three sections, show the ad before the third section
    if len(sections) >= 3:
        before = TAG.join(sections[0:2])
        after = TAG.join(sections[2:])
        if after:
            # we lost one <h3 because of the section splitting
            after = TAG + after

        return (before, after)

    # otherwise, just show it at the end
    return (content, "")


@register.inclusion_tag("fds_blog/blog_preview.html", takes_context=True)
def get_blog_preview(context, amount=6):
    amount = min(int(amount), 20)
    articles = Article.published.all()[:amount]

    return {"articles": articles, "request": context.get("request")}
