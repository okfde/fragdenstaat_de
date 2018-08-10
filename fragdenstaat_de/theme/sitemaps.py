from datetime import timedelta
from django.utils import timezone

from djangocms_blog.sitemaps import BlogSitemap


class NewsSitemap(BlogSitemap):
    def items(self):
        """
        Return published entries.
        """
        items = super(NewsSitemap, self).items()
        two_days_ago = timezone.now() - timedelta(hours=48)
        return [i for i in items if i.date_published >= two_days_ago]
