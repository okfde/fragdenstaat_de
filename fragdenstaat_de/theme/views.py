from django.shortcuts import render, Http404
from django.template import TemplateDoesNotExist


def show_press(request, slug=None):
    if slug is None:
        return render(request, 'press/index.html')
    try:
        return render(request, 'press/%s.html' % slug)
    except TemplateDoesNotExist:
        raise Http404
