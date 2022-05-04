from django.utils.translation import gettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import TEMPLATES, LatestArticlesPlugin


@plugin_pool.register_plugin
class BlogContent(CMSPluginBase):
    module = "Blog"
    render_template = "fds_blog/plugins/blog_content.html"
    allow_children = True


class BlogPlugin(CMSPluginBase):
    module = "Blog"

    def get_render_template(self, context, instance, placeholder):
        return instance.template or TEMPLATES[0][0]


class BlogLatestArticlesPlugin(BlogPlugin):
    """
    Non cached plugin which returns the latest posts taking into account the
      user / toolbar state
    """

    name = _("Latest Blog Articles")
    model = LatestArticlesPlugin
    filter_horizontal = ("categories",)
    cache = False

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["article_list"] = instance.get_articles(
            context["request"], published_only=False
        )
        return context


class BlogLatestArticlesPluginCached(BlogPlugin):
    """
    Cached plugin which returns the latest published posts
    """

    name = _("Latest Blog Articles - Cache")
    model = LatestArticlesPlugin
    filter_horizontal = ("categories",)

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["article_list"] = instance.get_articles(context["request"])
        return context


plugin_pool.register_plugin(BlogLatestArticlesPlugin)
plugin_pool.register_plugin(BlogLatestArticlesPluginCached)
