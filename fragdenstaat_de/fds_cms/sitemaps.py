from django.db.models import OuterRef, Q, Subquery

from cms.models import PageContent, PageUrl
from cms.sitemaps import CMSSitemap
from cms.utils import get_current_site
from cms.utils.i18n import get_public_languages


class FdsCMSSitemap(CMSSitemap):
    def items(self):
        """
        Copy from CMSSitemap and filter further by fds page extension
        """
        site = get_current_site()
        languages = get_public_languages(site_id=site.pk)

        return list(
            PageUrl.objects.get_for_site(site)
            .filter(
                language__in=languages, path__isnull=False, page__login_required=False
            )
            .order_by("page__node__path")
            .select_related("page")
            .annotate(
                content_pk=Subquery(
                    PageContent.objects.filter(
                        page=OuterRef("page"), language=OuterRef("language")
                    )
                    .filter(Q(redirect="") | Q(redirect=None))
                    .values_list("pk")[:1]
                )
            )
            .filter(content_pk__isnull=False)  # Remove page content with redirects
            .filter(  # Remove when page is not supposed to be indexed
                Q(page__fdspageextension=None)
                | Q(page__fdspageextension__search_index=True)
            )
        )
