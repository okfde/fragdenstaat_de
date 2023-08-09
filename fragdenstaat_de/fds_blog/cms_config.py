from django.template.response import TemplateResponse

from cms.app_base import CMSAppConfig

from .models import Article


def render_article_content(request, article):
    template = "fds_blog/article_detail.html"
    context = {
        "article": article,
        "force_cms_render": True,
        "CMS_TEMPLATE": "cms/blog_base.html",
    }
    return TemplateResponse(request, template, context)


class ArticleCMSConfig(CMSAppConfig):
    cms_enabled = True
    cms_toolbar_enabled_models = [(Article, render_article_content)]
