from django.shortcuts import render, Http404
from django.template import TemplateDoesNotExist

from froide.helper.cache import cache_anonymous_page


@cache_anonymous_page(15 * 60)
def show_press(request, slug=None):
    if slug is None:
        return render(request, 'press/index.html')
    try:
        return render(request, 'press/%s.html' % slug)
    except TemplateDoesNotExist:
        raise Http404
