from datetime import timedelta

from django.contrib.sitemaps import Sitemap
from django.conf import settings
from django.utils import timezone

from .models import Article


class BlogSitemap(Sitemap):
    priority = 1.0
    changefreq = 'daily'
    protocol = settings.META_SITE_PROTOCOL

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_cache = {}

    def items(self):
        return Article.published.all()

    def lastmod(self, obj):
        return obj.last_update


class NewsSitemap(BlogSitemap):
    def items(self):
        """
        Return published entries.
        """
        items = super(NewsSitemap, self).items()
        two_days_ago = timezone.now() - timedelta(hours=48)
        return items.filter(start_publication__gte=two_days_ago)
