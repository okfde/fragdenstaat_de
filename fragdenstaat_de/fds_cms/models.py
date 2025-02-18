from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import NoReverseMatch
from django.utils.translation import gettext_lazy as _

from cms.extensions import PageExtension
from cms.extensions.extension_pool import extension_pool
from cms.models.fields import PageField
from cms.models.pluginmodel import CMSPlugin
from datashow.models import Dataset, Table
from djangocms_frontend.fields import AttributesField, TagTypeField
from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField
from filingcabinet.models import DocumentPortal, PageAnnotation
from taggit.models import Tag

from froide.document.models import Document, DocumentCollection
from froide.foirequest.models import FoiProject, FoiRequest
from froide.publicbody.models import Category, Classification, Jurisdiction, PublicBody

from fragdenstaat_de.theme.colors import BACKDROP, BACKGROUND, get_css_color_variable


def validate_space_separated_urls(value):
    if not value:
        return
    if ";" in value:
        # Prevent adding different policy directives.
        raise ValidationError("Use space separated URLs, no semicolons allowed.")
    if len(value.splitlines()) > 1:
        # Prevent header injection.
        raise ValidationError("No line breaks allowed.")
    for url in value.split(" "):
        if not url.startswith("https://"):
            raise ValidationError("Invalid URL: %s" % url)


@extension_pool.register
class FdsPageExtension(PageExtension):
    search_index = models.BooleanField(
        _("Show in search results and search engines"), default=True
    )
    image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=_("image"),
    )
    breadcrumb_ancestor = PageField(
        null=True,
        blank=True,
        help_text=_(
            "If present, this page will be displayed as the ancestor in the breadcrumbs."
        ),
        verbose_name=_("Ancestor"),
        related_name="breadcrumb_ancestor",
    )
    ancestor_only_upwards = models.BooleanField(
        _("Only show the breadcrumb ancestor on this page, but not its children"),
        default=True,
    )
    breadcrumb_background = models.CharField(
        _("Breadcrumbs background"),
        choices=BACKGROUND,
        default="",
        max_length=50,
        blank=True,
    )
    breadcrumb_overlay = models.BooleanField(
        _(
            "Lay the breadcrumbs over the page content. Works well with hero image headers."
        ),
        default=False,
    )
    frame_ancestors = models.CharField(
        _("Space separated list of allowed frame ancestor URLs."),
        max_length=255,
        blank=True,
        validators=[validate_space_separated_urls],
    )

    def get_frame_ancestors(self):
        # Split by generic whitespace
        return self.frame_ancestors.split()


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
    description = models.TextField(
        blank=True, help_text=_("Formatting with Markdown is supported.")
    )

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


class DesignContainerCMSPlugin(CMSPlugin):
    background = models.CharField(
        _("Background"), choices=BACKGROUND, default="", max_length=50, blank=True
    )
    backdrop = models.CharField(
        _("Backdrop"), choices=BACKDROP, max_length=5, default="", blank=True
    )
    extra_classes = models.CharField(max_length=255, blank=True)
    container = models.BooleanField(default=True)
    padding = models.BooleanField(default=True)

    def has_backdrop(self):
        return self.backdrop != ""


class ShareLinksCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=255)
    url = models.URLField(
        blank=True, help_text=_("Defaults to the current page's URL.")
    )
    icons_only = models.BooleanField(_("Only show icons"), default=False)

    image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=_("image"),
        help_text=_(
            "Only available with the Native Share API. If sharing doesn't work, the image will be downloaded instead."
        ),
    )

    bluesky = models.BooleanField("BlueSky", default=True)
    mastodon = models.BooleanField("Mastodon", default=True)
    facebook = models.BooleanField("Facebook", default=False)
    email = models.BooleanField(_("Email"), default=False)
    clipboard = models.BooleanField(_("Copy to clipboard"), default=True)
    native_share = models.BooleanField(
        _("Native share"), default=True, help_text=_("Great on mobile devices.")
    )
    native_text = models.CharField(
        _("Native share button label"), blank=True, max_length=50, default=""
    )
    native_links = models.BooleanField(
        _("Link instead of button"),
        default=False,
    )

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

    def css_color_variable(self):
        return get_css_color_variable(self.color)

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


class PretixEmbedCMSPlugin(CMSPlugin):
    shop_url = models.CharField()
    js_url = models.CharField()
    additional_settings = models.CharField(default="", blank=True)


class DatashowDatasetTheme(models.Model):
    dataset = models.OneToOneField(
        Dataset, on_delete=models.CASCADE, related_name="theme"
    )

    image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("image"),
    )
    banner = FilerImageField(
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("banner image"),
    )

    def __str__(self):
        return "Theme for %s" % self.dataset


class DatashowTableCMSPlugin(CMSPlugin):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    query = models.TextField(blank=True)
    limit = models.SmallIntegerField(default=10)

    def __str__(self):
        return self.table.label
