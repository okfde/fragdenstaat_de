
from django.shortcuts import render

from froide.foirequest.models import FoiRequest
from froide.publicbody.models import PublicBody
from froide.frontpage.models import FeaturedRequest
from froide.helper.cache import cache_anonymous_page


@cache_anonymous_page(15 * 60)
def index(request):
    successful_foi_requests = FoiRequest.published.successful()[:6]
    unsuccessful_foi_requests = FoiRequest.published.unsuccessful()[:4]
    featured = FeaturedRequest.objects.get_queryset().order_by("-timestamp").select_related('request', 'request__public_body')[:3]
    return render(request, 'index.html',
            {'featured': featured[0],
            'featured1': featured[1],
            'featured2': featured[2],
            'successful_foi_requests': successful_foi_requests,
            'unsuccessful_foi_requests': unsuccessful_foi_requests,
            'foicount': FoiRequest.published.for_list_view().count(),
            'pbcount': PublicBody.objects.get_list().count()
})


def bundestag(request):
    return render_to_response('fragdenbundestag.html', {})
