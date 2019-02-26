from django.urls import reverse_lazy

from cms.models import Title

from froide.helper.search.views import BaseSearchView
from froide.helper.search.filters import BaseSearchFilterSet

from .documents import CMSDocument


class CMSFilterset(BaseSearchFilterSet):
    query_fields = ['title^5', 'description^3', 'content']


class CMSPageSearch(BaseSearchView):
    search_name = 'cms'
    template_name = 'fds_cms/search.html'
    object_template = 'fds_cms/result_item.html'
    model = Title
    document = CMSDocument
    filterset = CMSFilterset
    search_url = reverse_lazy('fds_cms:fds_cms-search')
