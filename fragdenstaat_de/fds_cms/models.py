from django.db import models

from cms.models.pluginmodel import CMSPlugin

from froide.document.models import Document, Page, PageAnnotation


class PageAnnotationCMSPlugin(CMSPlugin):
    page_annotation = models.ForeignKey(PageAnnotation, related_name='+',)

    def __str__(self):
        return str(self.page_annotation)


class DocumentPagesCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    doc = models.ForeignKey(Document, related_name='+',)
    pages = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return '%s: %s' % (self.doc, self.pages)

    def get_pages(self):
        page_numbers = list(self.get_page_numbers())
        return self.doc.page_set.filter(number__in=page_numbers)

    def get_page_numbers(self):
        if not self.pages:
            yield from range(1, self.doc.num_pages + 1)
            return
        parts = self.pages.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                start_stop = part.split('-')
                yield from range(int(start_stop[0]), int(start_stop[1]) + 1)
            else:
                yield int(part)
        
