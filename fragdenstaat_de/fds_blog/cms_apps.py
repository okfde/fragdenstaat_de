from django.utils.translation import ugettext_lazy as _

from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool


@apphook_pool.register
class FdsBlogApp(CMSApp):
    name = _('FragDenStaat-Blog')
    app_name = 'blog'

    def get_urls(self, page=None, language=None, **kwargs):
        return ['fragdenstaat_de.fds_blog.urls']
