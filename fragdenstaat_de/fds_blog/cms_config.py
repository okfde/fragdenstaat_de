from django.template.response import TemplateResponse

from cms.app_base import CMSAppConfig

from .models import Article


def get_author_groups(article):
    """Helper function to group authors by profile availability"""
    all_authors = list(article.get_authors())
    authors_with_profiles = []
    authors_without_profiles = []

    for author in all_authors:
        if (
            author.user
            and getattr(author.user, "profile_text", None)
            and author.user.profile_text.strip()
        ):
            authors_with_profiles.append(author)
        else:
            authors_without_profiles.append(author)

    return authors_with_profiles, authors_without_profiles


def render_article_content(request, article):
    template = "fds_blog/article_detail.html"
    authors_with_profiles, authors_without_profiles = get_author_groups(article)

    context = {
        "article": article,
        "force_cms_render": True,
        "CMS_TEMPLATE": "cms/blog_base.html",
        "authors_with_profiles": authors_with_profiles,
        "authors_without_profiles": authors_without_profiles,
    }
    return TemplateResponse(request, template, context)


class ArticleCMSConfig(CMSAppConfig):
    cms_enabled = True
    cms_toolbar_enabled_models = [(Article, render_article_content)]
