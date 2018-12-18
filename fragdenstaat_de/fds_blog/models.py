import uuid

from django.db import models
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils import translation
from django.urls import reverse
from django.utils import html
from django.contrib.sites.shortcuts import get_current_site

from cms.models.pluginmodel import CMSPlugin
from cms.models.fields import PlaceholderField

from parler.models import TranslatableModel, TranslatedFields
from filer.fields.image import FilerImageField

from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase, TagBase

from . import model_bases as entry
from .utils import get_request
from .managers import (
    ArticlePublishedManager, CategoryManager, RelatedPublishedManager,
    articles_published
)


class AuthorManager(models.Manager):
    def get_by_user(self, user):
        try:
            return self.get_queryset().get(user=user)
        except Author.DoesNotExist:
            return None


class Author(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True, related_name='authorship', blank=True,
        on_delete=models.SET_NULL
    )
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    email_address = models.CharField(max_length=255, blank=True)

    objects = AuthorManager()
    published = RelatedPublishedManager()

    class Meta:
        ordering = ('user__first_name', 'user__last_name', 'first_name', 'last_name')

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
        return '%s %s' % (self.first_name, self.last_name)

    def get_short_name(self):
        """
        Returns author's published entries.
        """
        user = self.user or self

        if len(user.first_name) > 0 and len(user.last_name) > 0:
            return html.format_html(u"{}.&nbsp;{}",
                user.first_name[0],
                user.last_name,
            )
        else:
            return user.last_name or user.first_name

    def get_absolute_url(self):
        if self.user:
            return reverse('blog:article-author', kwargs={
                'username': self.user.username
            })
        return ''

    def get_avatar(self):
        if self.user:
            return self.user.avatar
        return None

    def get_username(self):
        return self.user.get_username() if self.user else 'none'


class ArticleAuthorship(models.Model):
    article = models.ForeignKey('Article', on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('order',)

    def __str__(self):
        return u'%s' % self.author


class OrderedAuthorsEntry(models.Model):
    """
    Abstract model class to add relationship
    between the entries and their authors.
    """
    authors = models.ManyToManyField(
        Author,
        through=ArticleAuthorship,
        related_name='articles',
        blank=True,
        verbose_name=_('authors'))

    class Meta:
        abstract = True


class Category(TranslatableModel):
    """
    Simple model for categorizing entries.
    """
    translations = TranslatedFields(
        title=models.CharField(
            _('title'), max_length=255),
        slug=models.SlugField(
            _('slug'), unique=False, max_length=255,
            help_text=_("Used to build the category's URL.")),
        description=models.TextField(
            _('description'), blank=True)
    )
    order = models.PositiveIntegerField(default=0)

    objects = CategoryManager()
    published = RelatedPublishedManager()

    class Meta:
        """
        Category's meta informations.
        """
        ordering = ['order']
        verbose_name = _('category')
        verbose_name_plural = _('categories')

    def __str__(self):
        return self.title

    def articles_published(self):
        """
        Returns category's published entries.
        """
        return articles_published(self.articles)


class CategoriesEntry(models.Model):
    """
    Abstract model class to categorize the entries.
    """
    categories = models.ManyToManyField(
        Category,
        related_name='articles',
        blank=True,
        verbose_name=_('categories'))

    class Meta:
        abstract = True


class ArticleTag(TagBase):
    class Meta:
        verbose_name = _("Article Tag")
        verbose_name_plural = _("Article Tags")


class TaggedArticle(TaggedItemBase):
    tag = models.ForeignKey(
        ArticleTag, related_name="articles",
        on_delete=models.CASCADE)
    content_object = models.ForeignKey(
        'Article',
        on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Tagged Article')
        verbose_name_plural = _('Tagged Articles')


class TagsEntry(models.Model):
    tags = TaggableManager(through=TaggedArticle, blank=True)

    class Meta:
        abstract = True

    @property
    def tag_list(self):
        return u", ".join(o.name for o in self.tags.all())


class LanguageEntry(models.Model):
    language = models.CharField(
        max_length=5,
        editable=True, blank=False, null=True,
        choices=settings.LANGUAGES
    )
    uuid = models.UUIDField(db_index=True, null=True, blank=True)

    class Meta:
        abstract = True


class CMSContentEntry(models.Model):
    content_placeholder = PlaceholderField('content')

    class Meta:
        abstract = True


class ArticleImageEntry(models.Model):
    image = FilerImageField(null=True, blank=True,
            default=None, verbose_name=_("image"),
            on_delete=models.SET_NULL
    )

    class Meta:
        abstract = True


class FeaturedEntry(models.Model):
    date_featured = models.DateTimeField(
        _('featured date'), null=True, blank=True
    )

    class Meta:
        abstract = True


class DetailsEntry(models.Model):
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
        LanguageEntry):

    objects = ArticleManager()
    published = ArticlePublishedManager()

    class Meta:
        verbose_name = _('article')
        verbose_name_plural = _('articles')
        ordering = ['-start_publication']
        get_latest_by = 'start_publication'
        unique_together = (('slug', 'start_publication'),)
        index_together = [['slug', 'start_publication'],
                          ['status', 'start_publication', 'end_publication']]

    def __str__(self):
        return _('Article "%s"') % self.title

    @property
    def description(self):
        return self.subheadline or self.excerpt

    def get_html_content(self, request=None, template='fds_blog/content.html'):
        if request is None:
            request = get_request(language=self.language)
        context = {
            'placeholder': self.content_placeholder,
            'lang': self.language,
            'object': self
        }
        return render_to_string(template, context=context, request=request)

    def get_full_html_content(self, request=None):
        return self.get_html_content(
            request=request, template='fds_blog/full_content.html'
        )

    def get_absolute_url(self, language=None, nopage=False):
        """
        Builds and returns the entry's URL based on
        the slug and the creation date, app namespace, page link...
        """

        cur_language = translation.get_language()

        language = language or self.language

        try:
            if language:
                translation.activate(language)

            publication_date = self.publication_date
            kwargs = {
                'slug': self.slug
            }
            if publication_date is not None:
                kwargs.update({
                    'year': publication_date.strftime('%Y'),
                    'month': publication_date.strftime('%m'),
                    'day': publication_date.strftime('%d'),
                })
            url = reverse('blog:article-detail', kwargs=kwargs)
        finally:
            if language:
                translation.activate(cur_language)
        return url

    def get_absolute_edit_url(self):
        return self.get_absolute_url(nopage=True)

    def get_full_url(self):
        return '%s%s' % (
            settings.SITE_URL,
            self.get_absolute_url()
        )

    def other_languages(self):
        if not hasattr(self, '_other_languages'):
            if self.uuid is None:
                self._other_languages = self.__class__.objects.none()
            else:
                self._other_languages = articles_published(self.__class__.objects
                                 .filter(uuid=self.uuid)
                                 .exclude(pk=self.pk))
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
        if not hasattr(self, '_cached_authors'):
            self._cached_authors = (Author.objects.filter(
                articleauthorship__article=self).order_by(
                'articleauthorship__order'))
        return self._cached_authors


TEMPLATES = [
    ('fds_blog/plugins/latest_articles.html', _('Normal')),
]


class LatestArticlesPlugin(CMSPlugin):
    """
    CMS Plugin for displaying latest articles
    """

    featured = models.NullBooleanField(
        _('featured'),
        blank=True, null=True,
        choices=((True, _('Show featured articles only')),
                 (False, _('Hide featured articles'))))
    article_language = models.CharField(
        _('language'), blank=True, choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE, max_length=5)
    categories = models.ManyToManyField(
        'Category', verbose_name=_('categories'),
        blank=True)
    authors = models.ManyToManyField(
        'Author', verbose_name=_('authors'),
        blank=True)
    tags = models.ManyToManyField(
        ArticleTag, verbose_name=_('tags'),
        blank=True)

    number_of_articles = models.PositiveIntegerField(
        _('number of articles'), default=1,
        help_text=_('0 means all the articles'))
    offset = models.PositiveIntegerField(
        _('offset'), default=0,
        help_text=_('number of articles to skip from top of list'))
    template = models.CharField(
        _('template'), blank=True,
        max_length=250, choices=TEMPLATES,
        help_text=_('template used to display the plugin'))

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
        self.tags = old_instance.tags.all()
        self.authors = old_instance.authors.all()
        self.categories = old_instance.categories.all()

    def __str__(self):
        return _('%s entries') % self.number_of_articles

    def get_articles(self, request, published_only=True):
        if (published_only or not request or not getattr(request, 'toolbar', False) or
                not request.toolbar.edit_mode_active):
            articles = Article.published.all()
        else:
            articles = Article.objects.all()

        filters = {}

        filters['sites'] = get_current_site(request)
        if self.article_language:
            filters['language'] = self.article_language
        if self.featured is not None:
            filters['featured__isnull'] = not self.featured
        tag_list = self.tags.all().values_list('id', flat=True)
        if tag_list:
            filters['tags__in'] = tag_list
        cat_list = self.categories.all().values_list('id', flat=True)
        if cat_list:
            filters['categories__in'] = cat_list
        author_list = self.authors.all().values_list('id', flat=True)
        if author_list:
            filters['authors__in'] = author_list

        articles = articles.filter(**filters).distinct()
        articles = articles.prefetch_related(
            'categories', 'categories__translations',
            'authors', 'tags',
        )
        return articles[self.offset:self.number_of_articles]
