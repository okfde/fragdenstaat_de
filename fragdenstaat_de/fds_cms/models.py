from django.conf import settings
from django.db import models
from django.urls import NoReverseMatch
from django.utils.translation import gettext_lazy as _

from cms.extensions import PageExtension
from cms.extensions.extension_pool import extension_pool
from cms.models.fields import PageField
from cms.models.pluginmodel import CMSPlugin
from djangocms_bootstrap4.fields import AttributesField, TagTypeField
from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField
from filingcabinet.models import DocumentPortal, PageAnnotation
from taggit.models import Tag

from froide.document.models import Document, DocumentCollection
from froide.foirequest.models import FoiProject, FoiRequest
from froide.publicbody.models import Category, Classification, Jurisdiction, PublicBody


@extension_pool.register
class FdsPageExtension(PageExtension):
    search_index = models.BooleanField(default=True)
    image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=_("image"),
    )


class PageAnnotationCMSPlugin(CMSPlugin):
    page_annotation = models.ForeignKey(
        PageAnnotation, related_name="+", on_delete=models.CASCADE
    )
    zoom = models.BooleanField(default=True)

    def __str__(self):
        return str(self.page_annotation)


class DocumentEmbedCMSPlugin(CMSPlugin):
    doc = models.ForeignKey(Document, related_name="+", on_delete=models.CASCADE)
    page_number = models.PositiveIntegerField(default=1)
    settings = models.TextField(default="{}")

    def __str__(self):
        return "Embed %s" % (self.doc,)


class DocumentCollectionEmbedCMSPlugin(CMSPlugin):
    collection = models.ForeignKey(
        DocumentCollection, related_name="+", on_delete=models.CASCADE
    )
    settings = models.TextField(default="{}")

    def __str__(self):
        return "Embed %s" % (self.collection,)


class DocumentPortalEmbedCMSPlugin(CMSPlugin):
    portal = models.ForeignKey(
        DocumentPortal, related_name="+", on_delete=models.CASCADE
    )
    settings = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return "Portal Embed %s" % (self.portal,)


class DocumentPagesCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    doc = models.ForeignKey(Document, related_name="+", on_delete=models.CASCADE)
    pages = models.CharField(max_length=255, blank=True)
    size = models.CharField(
        default="small",
        max_length=10,
        choices=(
            ("small", _("Small")),
            ("normal", _("Normal")),
            ("large", _("Large")),
        ),
    )

    def __str__(self):
        return "%s: %s" % (self.doc, self.pages)

    def get_pages(self):
        page_numbers = list(self.get_page_numbers())
        pages = self.doc.pages.filter(number__in=page_numbers)
        for page in pages:
            page.image_url = getattr(page, "image_" + self.size, "image_small").url
        return pages

    def get_page_numbers(self):
        if not self.pages:
            yield from range(1, self.doc.num_pages + 1)
            return
        parts = self.pages.split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                start_stop = part.split("-")
                yield from range(int(start_stop[0]), int(start_stop[1]) + 1)
            else:
                yield int(part)


class PrimaryLinkCMSPlugin(CMSPlugin):
    TEMPLATES = [
        ("", _("Default template")),
        ("featured.html", _("Featured template")),
        ("campaign.html", _("Campaign template")),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=_("image"),
    )

    url = models.CharField(
        _("link"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("if present image will be clickable"),
    )
    page_link = PageField(
        null=True,
        blank=True,
        help_text=_("if present image will be clickable"),
        verbose_name=_("page link"),
    )
    anchor = models.CharField(
        _("anchor"), max_length=128, blank=True, help_text=_("Page anchor.")
    )

    link_label = models.CharField(max_length=255, blank=True)
    extra_classes = models.CharField(max_length=255, blank=True)

    template = models.CharField(
        _("Template"), choices=TEMPLATES, default="", max_length=50, blank=True
    )

    def __str__(self):
        return self.title

    def link(self):
        if self.url:
            link = self.url
        elif self.page_link_id:
            try:
                link = self.page_link.get_absolute_url()
            except NoReverseMatch:
                link = ""
        else:
            link = ""
        if self.anchor:
            link += "#" + self.anchor
        return link


class FoiRequestListCMSPlugin(CMSPlugin):
    """
    CMS Plugin for displaying FoiRequests
    """

    TEMPLATES = [
        ("", _("Default template")),
        ("foirequest/cms_plugins/list_follow.html", _("Follow template")),
    ]

    resolution = models.CharField(
        blank=True, max_length=50, choices=FoiRequest.RESOLUTION.choices
    )

    status = models.CharField(
        blank=True, max_length=50, choices=FoiRequest.STATUS.choices
    )

    project = models.ForeignKey(
        FoiProject, null=True, blank=True, on_delete=models.SET_NULL
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    tags = models.ManyToManyField(Tag, verbose_name=_("tags"), blank=True)

    jurisdiction = models.ForeignKey(
        Jurisdiction, null=True, blank=True, on_delete=models.SET_NULL
    )
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL
    )
    classification = models.ForeignKey(
        Classification, null=True, blank=True, on_delete=models.SET_NULL
    )
    publicbody = models.ForeignKey(
        PublicBody, null=True, blank=True, on_delete=models.SET_NULL
    )

    number_of_entries = models.PositiveIntegerField(
        _("number of entries"), default=1, help_text=_("0 means all the entries")
    )
    offset = models.PositiveIntegerField(
        _("offset"),
        default=0,
        help_text=_("number of entries to skip from top of list"),
    )
    template = models.CharField(
        _("template"),
        blank=True,
        max_length=250,
        choices=TEMPLATES,
        help_text=_("template used to display the plugin"),
    )

    def __str__(self):
        return _("%s FOI requests") % self.number_of_entries

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


class OneClickFoiRequestCMSPlugin(CMSPlugin):
    TEMPLATES = [
        ("", _("Default template")),
    ]

    foirequest = models.ForeignKey(
        FoiRequest, related_name="+", on_delete=models.CASCADE
    )
    redirect_url = models.CharField(default="", max_length=255, blank=True)
    reference = models.CharField(default="", max_length=255, blank=True)

    template = models.CharField(
        _("Template"), choices=TEMPLATES, default="", max_length=50, blank=True
    )

    def __str__(self):
        return _("One click form for {}").format(self.foirequest)


class VegaChartCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    vega_json = models.TextField(
        default="",
    )

    def __str__(self):
        return self.title


class SVGImageCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255)

    svg = FilerFileField(
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=_("image"),
    )

    def __str__(self):
        return self.title


BACKGROUND = (
    [
        ("", _("None")),
        ("primary", _("Primary")),
        ("secondary", _("Secondary")),
        ("info", _("Info")),
        ("light", _("Light")),
        ("dark", _("Dark")),
        ("success", _("Success")),
        ("warning", _("Warning")),
        ("danger", _("Danger")),
        ("purple", _("Purple")),
        ("pink", _("Pink")),
        ("yellow", _("Yellow")),
        ("cyan", _("Cyan")),
        ("gray", _("Gray")),
        ("gray-dark", _("Gray Dark")),
        ("white", _("White")),
    ]
    + [("gray-{}".format(i), "Gray {}".format(i)) for i in range(100, 1000, 100)]
    + [
        ("blue-10", _("Blue 10")),
        ("blue-20", _("Blue 20")),
        ("blue-30", _("Blue 30")),
    ]
    + [("blue-{}".format(i), "Blue {}".format(i)) for i in range(100, 900, 100)]
    + [("yellow-{}".format(i), "Yellow {}".format(i)) for i in range(100, 400, 100)]
)


class DesignContainerCMSPlugin(CMSPlugin):
    TEMPLATES = [
        ("", _("Default template")),
        ("cms/plugins/designs/speech_bubble.html", _("Speech bubble")),
    ]

    template = models.CharField(
        _("Template"), choices=TEMPLATES, default="", max_length=50, blank=True
    )
    background = models.CharField(
        _("Background"), choices=BACKGROUND, default="", max_length=50, blank=True
    )
    extra_classes = models.CharField(max_length=255, blank=True)
    container = models.BooleanField(default=True)
    padding = models.BooleanField(default=True)


class ShareLinksCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255)
    url = models.URLField(blank=True)

    def __str__(self):
        return self.title


class CollapsibleCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    collapsed = models.BooleanField(default=True)

    extra_classes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title


class SliderCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    extra_classes = models.CharField(max_length=255, blank=True)
    options = models.TextField(blank=True)
    wrapper_classes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.title


class ModalCMSPlugin(CMSPlugin):
    identifier = models.CharField(max_length=255)
    tag_type = TagTypeField()
    attributes = AttributesField()
    dialog_attributes = AttributesField()

    def __str__(self):
        return self.identifier


class CardCMSPlugin(CMSPlugin):
    border = models.CharField(
        _("Border"),
        max_length=50,
        default="gray",
        choices=(
            ("none", _("None")),
            ("blue", _("Blue")),
            ("gray", _("Gray")),
            ("yellow", _("Yellow")),
        ),
    )
    shadow = models.CharField(
        _("Shadow"),
        max_length=10,
        default="no",
        choices=(("no", _("No")), ("auto", _("Auto")), ("always", _("Always"))),
    )
    spacing = models.CharField(
        _("Spacing"),
        max_length=3,
        default="md",
        choices=(
            ("sm", _("Small")),
            ("md", _("Medium")),
            ("lg", _("Large")),
        ),
    )
    background = models.CharField(
        _("Background"), choices=BACKGROUND, default="", max_length=50, blank=True
    )

    url = models.CharField(
        _("link"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("if present card will be clickable"),
    )
    page_link = PageField(
        null=True,
        blank=True,
        help_text=_("if present card will be clickable"),
        verbose_name=_("page link"),
    )

    attributes = AttributesField()

    def link(self):
        if self.url:
            return self.url
        elif self.page_link_id:
            try:
                return self.page_link.get_absolute_url()
            except NoReverseMatch:
                return


class CardInnerCMSPlugin(CMSPlugin):
    attributes = AttributesField()


class CardHeaderCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    icon = models.CharField(
        _("Icon"),
        max_length=50,
        blank=True,
        help_text=_(
            """Enter an icon name from the <a href="https://fontawesome.com/v4.7.0/icons/" target="_blank">FontAwesome 4 icon set</a>"""
        ),
    )
    background_image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("Background image"),
        on_delete=models.SET_NULL,
    )
    attributes = AttributesField()

    def __str__(self):
        return self.title


class CardImageCMSPlugin(CMSPlugin):
    image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=_("image"),
    )
    url = models.CharField(
        _("link"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("if present image will be clickable"),
    )
    page_link = PageField(
        null=True,
        blank=True,
        help_text=_("if present image will be clickable"),
        verbose_name=_("page link"),
    )
    overlap = models.CharField(
        _("Overlap"),
        choices=(("left", _("Left")), ("right", _("Right")), ("center", _("Center"))),
        max_length=10,
        default="right",
    )
    size = models.CharField(
        _("Size"),
        choices=(
            ("sm", _("Small")),
            ("lg", _("Large")),
            ("lg-wide", _("Large (wide)")),
        ),
        max_length=10,
        default="lg",
    )
    attributes = AttributesField()

    def link(self):
        if self.url:
            return self.url
        elif self.page_link_id:
            try:
                return self.page_link.get_absolute_url()
            except NoReverseMatch:
                return


class CardIconCMSPlugin(CMSPlugin):
    icon = models.CharField(
        max_length=255,
        blank=True,
        help_text=_(
            """Enter an icon name from the <a href="https://fontawesome.com/v4.7.0/icons/" target="_blank">FontAwesome 4 icon set</a>"""
        ),
    )
    attributes = AttributesField()

    def __str__(self):
        return self.icon


class CardLinkCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    url = models.CharField(_("link"), max_length=255, blank=True)
    page_link = PageField(blank=True, null=True)
    arrow = models.BooleanField(default=False)
    icon = models.CharField(
        _("Icon"),
        max_length=50,
        blank=True,
        help_text=_(
            """Enter an icon name from the <a href="https://fontawesome.com/v4.7.0/icons/" target="_blank">FontAwesome 4 icon set</a>"""
        ),
    )
    attributes = AttributesField()

    def link(self):
        if self.url:
            return self.url
        elif self.page_link_id:
            try:
                return self.page_link.get_absolute_url()
            except NoReverseMatch:
                return

    def __str__(self):
        return self.title


class RevealMoreCMSPlugin(CMSPlugin):
    cutoff = models.PositiveIntegerField(_("Cutoff after"), default=1)
    unit = models.CharField(
        _("Unit"),
        max_length=10,
        choices=(
            ("rows", _("grid rows")),
            ("rem", _("Line heights")),
            ("%", _("percent")),
        ),
    )
    color = models.CharField(_("Overlay color"), max_length=50, choices=BACKGROUND)
    reveal_text = models.CharField(_("Reveal text"), max_length=50, blank=True)
    attributes = AttributesField()

    def text(self):
        return self.reveal_text or str(_("Show more..."))

    def __str__(self):
        return self.text()


class BorderedSectionCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255, blank=True)
    border = models.CharField(
        _("Border"),
        max_length=50,
        default="gray",
        choices=(
            ("blue", _("Blue")),
            ("gray", _("Gray")),
            ("yellow", _("Yellow")),
        ),
    )
    spacing = models.CharField(
        _("Spacing"),
        max_length=3,
        default="md",
        choices=(
            ("sm", _("Small")),
            ("md", _("Medium")),
            ("lg", _("Large")),
        ),
    )
    heading = models.CharField(
        _("Heading level"),
        max_length=5,
        default="h3",
        choices=(
            ("h1", _("Headline 1")),
            ("h2", _("Headline 2")),
            ("h3", _("Headline 3")),
            ("h4", _("Headline 4")),
            ("h5", _("Headline 5")),
            ("h6", _("Headline 6")),
        ),
    )
    attributes = AttributesField()

    def __str__(self):
        return self.title


class DropdownBannerCMSPlugin(CMSPlugin):
    animation = models.BooleanField(_("Slide banner with animation"), default=True)
    dark = models.BooleanField(
        _("Banner is dark-themed, button should therefore be light"), default=False
    )
