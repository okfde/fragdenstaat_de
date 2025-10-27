import re
from typing import List, Tuple

from django import template

from ..models import Article, Author

register = template.Library()


@register.filter
def split_for_banner(content: str) -> Tuple[str, str]:
    # splits the content into content that is shown before the ad, and content that is shown after the ad

    # sections are split by h3 tags with an id attribute
    TAG = r'(<h3\s+[^>]*id="[^"]+".*?>.*?</h3>)'
    sections = re.split(TAG, content)

    # if there are at least three sections, show the ad before the third section
    if len(sections) >= 3:
        before = "".join(sections[0:3])
        after = "".join(sections[3:])

        return (before, after)

    # otherwise, just show it at the end
    return (content, "")


@register.inclusion_tag("fds_blog/blog_preview.html", takes_context=True)
def get_blog_preview(context, amount=6):
    amount = min(int(amount), 20)
    articles = Article.published.all()[:amount]

    return {"articles": articles, "request": context.get("request")}


@register.filter
def has_author_images(authors: List[Author]) -> bool:
    return any(author.user and author.user.profile_photo for author in authors)
