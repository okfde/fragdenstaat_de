import uuid
from typing import Optional

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.db import models
from django.db.models import Case, Q, Subquery, Value, When
from django.db.models.functions import Extract
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import html, translation
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from cms.models.fields import PlaceholderRelationField
from cms.models.pluginmodel import CMSPlugin
from cms.toolbar.utils import get_object_edit_url
from cms.utils.placeholder import get_placeholder_from_slot
from cms.utils.plugins import get_plugins
from djangocms_alias.models import Alias
from filer.fields.image import FilerImageField
from parler.models import TranslatableModel, TranslatedFields
from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase

from fragdenstaat_de.fds_cms.utils import get_request
from fragdenstaat_de.theme.colors import BACKGROUND

from . import model_bases as entry
from .managers import (
    ArticlePublishedManager,
    CategoryManager,
    RelatedPublishedManager,
    articles_published,
)


class Publication(models.Model):
    title = models.CharField(max_length=255)
    app_name = models.CharField(max_length=255, blank=True, unique=True)
    author = models.CharField(max_length=255, blank=True)

    description = models.TextField(blank=True)

    image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("image"),
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return self.title


class AuthorManager(models.Manager):
    def get_by_user(self, user):
        try:
            return self.get_queryset().get(user=user)
        except Author.DoesNotExist:
            return None


class Author(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        related_name="authorship",
        blank=True,
        on_delete=models.SET_NULL,
    )
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    email_address = models.CharField(max_length=255, blank=True)

    objects = AuthorManager()
    published = RelatedPublishedManager()

    class Meta:
        ordering = ("user__first_name", "user__last_name", "first_name", "last_name")

    @property
    def email(self):
        if self.user:
            return self.user.email
        return self.email_address

    @property
    def username(self):
        if self.user:
            return self.user.username
        return None

    def __str__(self):
        """
        If the user has a full name, use it instead of the username.
        """
        return self.user.get_full_name() if self.user else self.get_full_name()

    def articles_published(self):
        """
        Returns author's published entries.
        """
        return articles_published(self.articles)

    def get_full_name(self):
        if self.user:
            return self.user.get_full_name()
        return "%s %s" % (self.first_name, self.last_name)

    def get_short_name(self):
        """
        Returns author's published entries.
        """
        user = self.user or self

        if len(user.first_name) > 0 and len(user.last_name) > 0:
            return html.format_html(
                "{}.&nbsp;{}",
                user.first_name[0],
                user.last_name,
            )
        else:
            return user.last_name or user.first_name

    def get_absolute_url(self):
        if self.user:
            return reverse(
                "blog:article-author", kwargs={"username": self.user.username}
            )
        return ""

    def get_avatar(self):
        if self.user:
            return self.user.avatar
        return None

    def get_username(self):
        return self.user.get_username() if self.user else "none"


class ArticleAuthorship(models.Model):
    article = models.ForeignKey("Article", on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order",)

    def __str__(self):
        return "%s" % self.author


class OrderedAuthorsEntry(models.Model):
    """
    Abstract model class to add relationship
    between the entries and their authors.
    """

    authors = models.ManyToManyField(
        Author,
        through=ArticleAuthorship,
        related_name="articles",
        blank=True,
        verbose_name=_("authors"),
    )

    class Meta:
        abstract = True


class Category(TranslatableModel):
    """
    Simple model for categorizing entries.
    """

    translations = TranslatedFields(
        title=models.CharField(_("title"), max_length=255),
        slug=models.SlugField(
            _("slug"),
            unique=False,
            max_length=255,
            help_text=_("Used to build the category's URL."),
        ),
        description=models.TextField(_("description"), blank=True),
        meta={
            "constraints": [
                models.CheckConstraint(
                    check=~Q(slug__regex=r"^\d+$"),
                    name="not_just_digits_slug",
                    violation_error_message="The slug may not only consist of digits.",
                )
            ]
        },
    )
    order = models.PositiveIntegerField(default=0)

    color = models.CharField(
        _("Category color"),
        choices=BACKGROUND,
        default="",
        max_length=50,
        blank=True,
        help_text=_("Will be visible as the breadcrumb background."),
    )

    donation_banner = models.ForeignKey(
        Alias,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name="donation_banner",
        verbose_name=_("Donation banner"),
        help_text=_("Inserted after a couple of paragraphs on the article page."),
    )

    objects = CategoryManager()
    published = RelatedPublishedManager()

    class Meta:
        """
        Category's meta informations.
        """

        ordering = ["order"]
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def __str__(self):
        return self.title

    def articles_published(self):
        """
        Returns category's published entries.
        """
        return articles_published(self.articles)

    def get_absolute_url(self):
        return reverse("blog:article-category", kwargs={"slug": self.slug})


class CategoriesEntry(models.Model):
    """
    Abstract model class to categorize the entries.
    """

    categories = models.ManyToManyField(
        Category, related_name="articles", verbose_name=_("categories")
    )

    @cached_property
    def first_category(self) -> Optional[Category]:
        if self.categories.exists():
            return self.categories.first()

    class Meta:
        abstract = True


class ArticleTag(TagBase):
    class Meta:
        verbose_name = _("Article Tag")
        verbose_name_plural = _("Article Tags")

    def get_absolute_url(self):
        return reverse("blog:article-tagged", kwargs={"tag": self.slug})


class TaggedArticle(TaggedItemBase):
    tag = models.ForeignKey(
        ArticleTag, related_name="articles", on_delete=models.CASCADE
    )
    content_object = models.ForeignKey("Article", on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Tagged Article")
        verbose_name_plural = _("Tagged Articles")


class TagsEntry(models.Model):
    tags = TaggableManager(through=TaggedArticle, blank=True)

    class Meta:
        abstract = True

    @property
    def tag_list(self):
        return ", ".join(o.name for o in self.all_tags)

    @property
    def all_tags(self):
        if not hasattr(self, "_all_tags"):
            self._all_tags = self.tags.all()
        return self._all_tags


class LanguageEntry(models.Model):
    language = models.CharField(
        max_length=5, editable=True, blank=False, null=True, choices=settings.LANGUAGES
    )
    uuid = models.UUIDField(db_index=True, null=True, blank=True)

    class Meta:
        abstract = True


class CMSContentEntry(models.Model):
    placeholders = PlaceholderRelationField()

    class Meta:
        abstract = True

    @cached_property
    def content_placeholder(self):
        return get_placeholder_from_slot(self.placeholders, "content")

    @cached_property
    def header_placeholder(self):
        return get_placeholder_from_slot(self.placeholders, "header")

    @property
    def has_ad_plugin(self) -> bool:
        plugins = self.content_placeholder.get_plugins()
        return plugins.filter(plugin_type="BlogAd").exists()

    def get_template(self):
        return "fds_blog/placeholders.html"


class ArticleImageEntry(models.Model):
    image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("image"),
        on_delete=models.SET_NULL,
    )

    class Meta:
        abstract = True


class FeaturedEntry(models.Model):
    date_featured = models.DateTimeField(_("featured date"), null=True, blank=True)

    class Meta:
        abstract = True


class DetailsEntry(models.Model):
    kicker = models.CharField(max_length=100, blank=True)
    teaser = models.TextField(blank=True)
    credits = models.TextField(blank=True)

    class Meta:
        abstract = True


class ArticleManager(models.Manager):
    def mark_translations(self, queryset):
        uuid_val = None
        for article in queryset:
            if article.uuid:
                uuid_val = article.uuid
                break
        if uuid_val is None:
            uuid_val = uuid.uuid4()
        queryset.update(uuid=uuid_val)


class Article(
    entry.CoreEntry,
    FeaturedEntry,
    DetailsEntry,
    ArticleImageEntry,
    entry.ContentEntry,
    CMSContentEntry,
    entry.RelatedEntry,
    entry.ExcerptEntry,
    CategoriesEntry,
    TagsEntry,
    OrderedAuthorsEntry,
    entry.ContentTemplateEntry,
    entry.DetailTemplateEntry,
    LanguageEntry,
    entry.AudioEntry,
):
    objects = ArticleManager()
    published = ArticlePublishedManager()

    class Meta:
        verbose_name = _("article")
        verbose_name_plural = _("articles")
        ordering = ["-start_publication"]
        get_latest_by = "start_publication"
        constraints = [
            models.UniqueConstraint(
                "slug",
                "language",
                Extract("start_publication", "year"),
                Extract("start_publication", "month"),
                name="unique_blog_url",
                violation_error_message=_(
                    "An article with the same slug, month and year already exists. Please choose another slug."
                ),
            ),
        ]
        index_together = [
            ["slug", "start_publication"],
            ["status", "start_publication", "end_publication"],
        ]

    def __str__(self):
        return _('Article "%s"') % self.title

    @property
    def description(self):
        return self.teaser or self.excerpt

    @property
    def meta_title(self):
        if self.kicker:
            return "{}: {}".format(self.kicker, self.title)
        return self.title

    def get_html_content(self, request=None, template="fds_blog/content.html"):
        if request is None:
            request = get_request(language=self.language)

        plugins = get_plugins(
            request=request,
            placeholder=self.content_placeholder,
            template=template,
            lang=self.language,
        )
        blog_content_plugins = [p for p in plugins if p.plugin_type == "BlogContent"]

        context = {"plugins": blog_content_plugins, "object": self}
        return mark_safe(render_to_string(template, context=context, request=request))

    def get_full_html_content(self, request=None):
        return self.get_html_content(
            request=request, template="fds_blog/full_content.html"
        )

    def get_absolute_url(self, language=None, nopage=False):
        """
        Builds and returns the entry's URL based on
        the slug and the creation date, app namespace, page link...
        """

        cur_language = translation.get_language()

        language = language or self.language
        category = self.categories.language(language).first()

        try:
            if language:
                translation.activate(language)

            publication_date = self.publication_date
            kwargs = {
                "slug": self.slug,
                "year": publication_date.strftime("%Y"),
                "month": publication_date.strftime("%m"),
                "category": category.slug,
            }

            url = reverse("blog:article-detail", kwargs=kwargs)
        finally:
            if language:
                translation.activate(cur_language)
        return url

    def get_absolute_edit_url(self):
        return get_object_edit_url(self)

    def get_full_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_short_url(self):
        return "%s%s" % (
            settings.SITE_URL,
            reverse("article-short-url", kwargs={"pk": self.pk}),
        )

    def other_languages(self):
        if not hasattr(self, "_other_languages"):
            if self.uuid is None:
                self._other_languages = self.__class__.objects.none()
            else:
                self._other_languages = articles_published(
                    self.__class__.objects.filter(uuid=self.uuid).exclude(pk=self.pk)
                )
        return self._other_languages

    def get_language_url(self, lang):
        if self.language == lang:
            return self.get_absolute_url()
        qs = self.other_languages()
        try:
            return qs.get(language=lang).get_absolute_url()
        except Article.DoesNotExist:
            return None

    def get_detail_template(self):
        template = self.detail_template
        return template

    def get_authors(self):
        if not hasattr(self, "_cached_authors"):
            self._cached_authors = (
                Author.objects.filter(articleauthorship__article=self)
                .select_related("user")
                .order_by("articleauthorship__order")
            )
        return self._cached_authors

    def get_authors_string(self):
        return ", ".join(str(author) for author in self.get_authors())


TEMPLATES = [
    ("fds_blog/plugins/latest_articles.html", _("Normal")),
    ("fds_blog/plugins/featured_articles.html", _("Featured")),
    ("fds_blog/plugins/top_featured_articles.html", _("Top Featured")),
    ("fds_blog/plugins/simple_articles.html", _("Simple")),
]


class LatestArticlesPlugin(CMSPlugin):
    """
    CMS Plugin for displaying latest articles
    """

    featured = models.CharField(
        _("featured"),
        blank=True,
        null=True,
        max_length=5,
        choices=(
            ("show", _("Show featured articles only")),
            ("hide", _("Hide featured articles")),
            ("one", _("Only show one featured article")),
        ),
    )
    article_language = models.CharField(
        _("language"),
        blank=True,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
        max_length=5,
    )
    categories = models.ManyToManyField(
        "Category", verbose_name=_("categories"), blank=True
    )
    authors = models.ManyToManyField("Author", verbose_name=_("authors"), blank=True)
    tags = models.ManyToManyField(ArticleTag, verbose_name=_("tags"), blank=True)

    number_of_articles = models.PositiveIntegerField(
        _("number of articles"), default=1, help_text=_("0 means all the articles")
    )
    offset = models.PositiveIntegerField(
        _("offset"),
        default=0,
        help_text=_("number of articles to skip from top of list"),
    )
    template = models.CharField(
        _("template"),
        blank=True,
        max_length=250,
        choices=TEMPLATES,
        help_text=_("template used to display the plugin"),
    )

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
        self.authors.set(old_instance.authors.all())
        self.categories.set(old_instance.categories.all())

    def __str__(self):
        if self.number_of_articles == 0:
            return str(_("All articles"))
        return _("%s entries") % self.number_of_articles

    def get_articles(self, request, published_only=True):
        if (
            published_only
            or not request
            or not getattr(request, "toolbar", False)
            or not request.toolbar.edit_mode_active
        ):
            articles = Article.published.all()
        else:
            articles = Article.objects.all()

        filters = {}

        filters["sites"] = get_current_site(request)
        if self.article_language:
            filters["language"] = self.article_language
        if self.featured is not None:
            # for cms previews, we only care about one featured article
            if self.featured == "hide":
                filters["date_featured__isnull"] = True
            elif self.featured == "show":
                filters["date_featured__isnull"] = False
            else:
                # show one featured article at the top, then the rest in chronological order
                featured = articles.filter(date_featured__isnull=False).order_by(
                    "-date_featured"
                )

                articles = articles.annotate(
                    is_top_featured=Case(
                        When(pk=Subquery(featured.values("pk")[:1]), then=Value(1)),
                        default=Value(0),
                    )
                ).order_by("-is_top_featured", "-start_publication")

        tag_list = self.tags.all().values_list("id", flat=True)
        if tag_list:
            filters["tags__in"] = tag_list

        cat_list = self.categories.all().values_list("id", flat=True)
        if cat_list:
            filters["categories__in"] = cat_list

        author_list = self.authors.all().values_list("id", flat=True)
        if author_list:
            filters["authors__in"] = author_list

        articles = (
            articles.filter(**filters)
            .distinct()
            .prefetch_related(
                "categories",
                "categories__translations",
                "authors",
            )
        )
        if self.number_of_articles == 0:
            return articles[self.offset :]
        return articles[self.offset : self.offset + self.number_of_articles]


class ArticlePreviewPlugin(CMSPlugin):
    """
    CMS plugin to display one article preview
    """

    article = models.ForeignKey("Article", on_delete=models.CASCADE)
    template = models.CharField(
        _("template"),
        blank=True,
        max_length=250,
        choices=TEMPLATES,
        help_text=_("template used to display the plugin"),
    )

    @property
    def render_template(self):
        """
        Override render_template to use
        the template_to_render attribute
        """
        return self.template_to_render

    def __str__(self):
        if self.article:
            return self.article.title

        return ""


class DetailsBoxCMSPlugin(CMSPlugin):
    title = models.CharField(max_length=100, blank=True)
    content = models.TextField(blank=True)
    inline = models.BooleanField(default=False)


class InfotextboxCMSPlugin(CMSPlugin):
    content = models.TextField(blank=True)
