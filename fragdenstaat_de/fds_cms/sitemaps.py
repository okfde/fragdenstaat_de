from django.db.models import Q

from cms.sitemaps import CMSSitemap


class FdsCMSSitemap(CMSSitemap):
    def items(self):
        """
        Copy from CMSSitemap and filter further by fds page extension
        """
        return (
            super()
            .items()
            .filter(
                Q(page__fdspageextension=None)
                | Q(page__fdspageextension__search_index=True)
            )
        )
