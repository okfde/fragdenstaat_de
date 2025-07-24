from cms.app_base import CMSAppConfig

from fragdenstaat_de.fds_blog.views import ArticleDetailView

from .models import Article

view = ArticleDetailView.as_view()


def render_article_content(request, article):
    return view(request, article=article)


class ArticleCMSConfig(CMSAppConfig):
    cms_enabled = True
    cms_toolbar_enabled_models = [(Article, render_article_content)]
