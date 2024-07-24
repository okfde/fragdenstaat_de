"""Toolbar extensions for CMS"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool


class BlogToolbar(CMSToolbar):
    def populate(self):
        blog_menu = self.toolbar.get_or_create_menu("blog-menu", _("Blog"))

        if hasattr(self.request, "article"):
            article = self.request.article
            url = reverse("admin:fds_blog_article_change", args=(article.pk,))
            blog_menu.add_modal_item(_("Edit this article"), url=url)

        url = reverse("admin:fds_blog_article_changelist")
        blog_menu.add_modal_item(_("Article overview"), url=url)

        url = reverse("admin:fds_blog_article_add")
        blog_menu.add_modal_item(_("Create new article"), url=url)


toolbar_pool.register(BlogToolbar)
