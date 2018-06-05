from django.db import models
from django.utils.translation import ugettext_lazy as _

from cms.models.pluginmodel import CMSPlugin
from cms.models.fields import PageField

from filer.fields.image import FilerImageField

from froide.document.models import Document, PageAnnotation


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


class PrimaryLinkCMSPlugin(CMSPlugin):
    TEMPLATES = [
        ('', _('Default template')),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    image = FilerImageField(null=True, blank=True, default=None,
        on_delete=models.SET_NULL, verbose_name=_("image"))

    url = models.CharField(_("link"), max_length=255,
        blank=True, null=True,
        help_text=_("if present image will be clickable"))
    page_link = PageField(null=True, blank=True,
        help_text=_("if present image will be clickable"),
        verbose_name=_("page link"))
    anchor = models.CharField(_("anchor"),
        max_length=128, blank=True, help_text=_("Page anchor."))

    template = models.CharField(_('Template'), choices=TEMPLATES,
                                default='', max_length=50, blank=True)

    def __str__(self):
        return self.title

    def link(self):
        if self.url:
            link = self.url
        elif self.page_link_id:
            link = self.page_link.get_absolute_url()
        else:
            link = ""
        if self.anchor:
            link += '#' + self.anchor
        return link
