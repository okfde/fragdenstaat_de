"""Toolbar extensions for CMS"""
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool


class BlogToolbar(CMSToolbar):

    def populate(self):
        if not hasattr(self.request, 'article'):
            return

        blog_menu = self.toolbar.get_or_create_menu(
            'blog-menu', _('Blog')
        )
        article = self.request.article
        url = reverse('admin:fds_blog_article_change', args=(article.pk,))
        blog_menu.add_modal_item(_('Edit article'), url=url)


toolbar_pool.register(BlogToolbar)
