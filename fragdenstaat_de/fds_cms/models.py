from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from cms.models.pluginmodel import CMSPlugin
from cms.models.fields import PageField

from filer.fields.image import FilerImageField

from taggit.models import Tag

from filingcabinet.models import PageAnnotation

from froide.foirequest.models import FoiRequest, FoiProject
from froide.publicbody.models import (
    Jurisdiction, Category, Classification, PublicBody
)
from froide.document.models import Document


class PageAnnotationCMSPlugin(CMSPlugin):
    page_annotation = models.ForeignKey(
        PageAnnotation, related_name='+',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return str(self.page_annotation)


class DocumentEmbedCMSPlugin(CMSPlugin):
    doc = models.ForeignKey(
        Document, related_name='+',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return 'Embed %s' % (self.doc,)


class DocumentPagesCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    doc = models.ForeignKey(
        Document, related_name='+',
        on_delete=models.CASCADE
    )
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


class FoiRequestListCMSPlugin(CMSPlugin):
    """
    CMS Plugin for displaying FoiRequests
    """

    TEMPLATES = [
        ('', _('Default template')),
    ]

    resolution = models.CharField(
        blank=True, max_length=50,
        choices=FoiRequest.RESOLUTION_FIELD_CHOICES
    )

    status = models.CharField(
        blank=True, max_length=50,
        choices=FoiRequest.STATUS_FIELD_CHOICES
    )

    project = models.ForeignKey(
        FoiProject, null=True, blank=True,
        on_delete=models.SET_NULL)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL
    )

    tags = models.ManyToManyField(
        Tag, verbose_name=_('tags'), blank=True)

    jurisdiction = models.ForeignKey(
        Jurisdiction, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    category = models.ForeignKey(
        Category, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    classification = models.ForeignKey(
        Classification, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    publicbody = models.ForeignKey(
        PublicBody, null=True, blank=True,
        on_delete=models.SET_NULL
    )

    number_of_entries = models.PositiveIntegerField(
        _('number of entries'), default=1,
        help_text=_('0 means all the entries'))
    offset = models.PositiveIntegerField(
        _('offset'), default=0,
        help_text=_('number of entries to skip from top of list'))
    template = models.CharField(
        _('template'), blank=True,
        max_length=250, choices=TEMPLATES,
        help_text=_('template used to display the plugin'))

    def __str__(self):
        return _('%s FOI requests') % self.number_of_entries

    @property
    def render_template(self):
        """
        Override render_template to use
        the template_to_render attribute
        """
        return self.template_to_render

    def copy_relations(self, old_instance):
        """
        Duplicate ManyToMany relations on plugin copy
        """
        self.tags.set(old_instance.tags.all())
