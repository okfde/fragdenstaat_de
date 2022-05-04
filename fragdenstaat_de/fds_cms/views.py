from cms.models import Title

from froide.helper.search.filters import BaseSearchFilterSet
from froide.helper.search.views import BaseSearchView

from .documents import CMSDocument


class CMSFilterset(BaseSearchFilterSet):
    query_fields = ["title^5", "description^3", "content"]


class CMSPageSearch(BaseSearchView):
    search_name = "cms"
    template_name = "fds_cms/search.html"
    object_template = "fds_cms/result_item.html"
    model = Title
    document = CMSDocument
    filterset = CMSFilterset
    search_url_name = "fds_cms:fds_cms-search"

    def get_base_search(self):
        qs = super().get_base_search()
        url_prefix = self.request.path.rsplit("/", 2)[0] + "/"
        qs = qs.filter("prefix", **{"url.raw": {"value": url_prefix}})
        return qs.filter("term", language=self.request.LANGUAGE_CODE)
