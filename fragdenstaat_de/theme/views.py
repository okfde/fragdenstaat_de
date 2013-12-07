from django.shortcuts import render, Http404
from django.template import TemplateDoesNotExist


def show_press(request, slug):
    try:
        return render(request, 'press/%s.html' % slug)
    except TemplateDoesNotExist:
        raise Http404
