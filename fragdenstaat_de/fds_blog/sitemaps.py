from datetime import timedelta

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.contrib.sites.models import Site
from django.utils import timezone

from .models import Article


class BlogSitemap(Sitemap):
    priority = 1.0
    changefreq = "daily"
    protocol = settings.META_SITE_PROTOCOL

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_cache = {}

    def items(self):
        site = Site.objects.get_current()
        return Article.published.on_site(site)

    def lastmod(self, obj):
        return obj.last_update


class NewsSitemap(BlogSitemap):
    def items(self):
        """
        Return published entries.
        """
        items = super().items()
        two_days_ago = timezone.now() - timedelta(hours=48)
        latest_items = items.filter(start_publication__gte=two_days_ago)
        if latest_items.count() == 0:
            # If no items are present in time frame, return the last two
            return items[:2]
        return latest_items
