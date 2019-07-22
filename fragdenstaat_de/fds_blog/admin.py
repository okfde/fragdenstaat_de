from django.utils import timezone
from django import forms
from django.contrib import admin
from django.contrib.sites.models import Site
from django.urls import NoReverseMatch
from django.db.models import Count
from django.utils.encoding import smart_text
from django.utils.translation import ungettext_lazy, ugettext_lazy as _
from django.utils.html import format_html

from adminsortable2.admin import SortableInlineAdminMixin
from parler.admin import TranslatableAdmin
from djangocms_text_ckeditor.widgets import TextEditorWidget
from cms.api import add_plugin
from cms.admin.placeholderadmin import PlaceholderAdminMixin

from froide.helper.admin_utils import make_nullfilter

from .models import (
    Article, Author, Category, ArticleTag, TaggedArticle
)
from .documents import index_article


class RelatedPublishedFilter(admin.SimpleListFilter):
    """
    Base filter for related objects to published articles.
    """
    model = None
    lookup_key = None

    def lookups(self, request, model_admin):
        """
        Return published objects with the number of articles.
        """
        active_objects = self.model.published.all().annotate(
            count_articles_published=Count('articles')).order_by(
            '-count_articles_published', '-pk').prefetch_related('translations')
        for active_object in active_objects:
            yield (
                str(active_object.pk), ungettext_lazy(
                    '%(item)s (%(count)i entry)',
                    '%(item)s (%(count)i articles)',
                    active_object.count_articles_published) % {
                    'item': smart_text(active_object),
                    'count': active_object.count_articles_published}
            )

    def queryset(self, request, queryset):
        """
        Return the object's articles if a value is set.
        """
        if self.value():
            params = {self.lookup_key: self.value()}
            return queryset.filter(**params)


class CategoryAdmin(TranslatableAdmin):
    fields = ('title', 'description', 'slug', 'order',)
    list_display = ('title',)
    search_fields = ('translations__title', 'translations__description')

    def get_prepopulated_fields(self, request, obj=None):
        # can't use `prepopulated_fields = ..` because it breaks the admin validation
        # for translated fields. This is the official django-parler workaround.
        return {
            'slug': ('title',)
        }


class CategoryListFilter(RelatedPublishedFilter):
    """
    List filter for EntryAdmin about categories
    with published articles.
    """
    model = Category
    lookup_key = 'categories__id'
    title = _('published categories')
    parameter_name = 'category'


class AuthorAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)


class AuthorshipInlineAdmin(SortableInlineAdminMixin, admin.TabularInline):
    model = Article.authors.through
    raw_id_fields = ('author',)


class ArticleAdminForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'
        widgets = {
            'teaser': TextEditorWidget()
        }


class ArticleAdmin(PlaceholderAdminMixin, admin.ModelAdmin):
    form = ArticleAdminForm
    date_hierarchy = 'start_publication'

    fieldsets = (
        (_('Content'), {
            'fields': ('title', 'status', 'teaser', 'image',),
        }),
        (_('URL'), {
            'fields': ('slug', 'start_publication'),
            'description': _('Make sure these are correct before publication. Do not change after publication!')
        }),
        (_('Additional Content'), {
            'fields': ('categories', 'tags', 'credits',)
        }),
        (_('Templates'), {
            'fields': ('content_template', 'detail_template'),
            'classes': ('collapse', 'collapse-closed')
        }),
        (_('Publication Dates'), {
            'fields': (('creation_date', 'end_publication', 'date_featured'),
            ),
            'classes': ('collapse', 'collapse-closed')
        }),
        (_('Metadata'), {
            'fields': ('excerpt', 'related', ),
            'classes': ('collapse', 'collapse-closed')
        }),
        (_('Advanced'), {
            'fields': ('language', 'uuid', 'sites'),
            'classes': ('collapse', 'collapse-closed')
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('title', 'slug', 'language',)}
        ),
    )
    inlines = (AuthorshipInlineAdmin,)
    list_display = (
        'get_title',
        'get_edit_link',
        'get_authors',
        'get_categories',
        'language',
        'get_is_visible',
        'has_translation',
        'start_publication'
    )

    list_filter = (
        'status',
        CategoryListFilter,
        make_nullfilter('categories', 'Hat Kategorie'),
        'tags',
        'date_featured',
        'language',
        make_nullfilter('image', 'Hat Bild'),
        'sites',
        'creation_date', 'start_publication', 'end_publication',
    )
    radio_fields = {'content_template': admin.VERTICAL,
                    'detail_template': admin.VERTICAL}
    prepopulated_fields = {'slug': ('title', )}
    search_fields = ('title', 'excerpt', 'content', 'tags__name')

    raw_id_fields = ('related',)
    filter_horizontal = ('categories', 'authors',)
    save_on_top = True

    actions = ['set_language']
    actions_on_top = True
    actions_on_bottom = True

    # def __init__(self, model, admin_site):
    #     # self.form.admin_site = admin_site
    #     super().__init__(model, admin_site)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related(
            'categories', 'categories__translations',
            'authors', 'authors__user',
        )
        return qs

    def get_changeform_initial_data(self, request):
        """
        Provide initial datas when creating an entry.
        """
        get_data = super().get_changeform_initial_data(request)
        return get_data or {
            'sites': [Site.objects.get_current().pk],
            'authors': [request.user.pk]
        }

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def save_model(self, request, article, form, change):
        """
        Save the update time.
        """
        if change:
            content = article.get_html_content(request)
            article.content = content or ''

        article.last_update = timezone.now()

        public_changed = False
        if 'status' in form.changed_data or 'start_publication' in form.changed_data:
            public_changed = True

        super().save_model(request, article, form, change)

        article.save()

        if public_changed:
            index_article(article)

        if not change:
            article.sites.add(Site.objects.get_current())
            add_plugin(article.content_placeholder, 'TextPlugin',
                       article.language, body='')

    def get_title(self, article):
        """
        Return the title with word count and number of comments.
        """
        return article.title
    get_title.short_description = _('title')

    def get_authors(self, article):
        """
        Return the authors in HTML.
        """
        return ', '.join(str(author) for author in article.authors.all())
    get_authors.short_description = _('author(s)')

    def get_categories(self, article):
        """
        Return the categories linked in HTML.
        """
        categories = [category.title for category in
                      article.categories.all()]
        return ', '.join(categories)
    get_categories.short_description = _('category(s)')

    def get_is_visible(self, article):
        """
        Admin wrapper for article.is_visible.
        """
        return article.is_visible
    get_is_visible.boolean = True
    get_is_visible.short_description = _('is visible')

    def get_edit_link(self, article):
        """
        Return the authors in HTML.
        """
        try:
            edit_link = article.get_absolute_edit_url()
        except NoReverseMatch:
            return _('unavailable for this site')
        return format_html('<a href="{url}" target="_blank">{title}</a>',
            url=edit_link + '?edit',
            title=_('Edit Content')
        )
    get_edit_link.short_description = _('Content')

    def has_translation(self, article):
        return bool(article.uuid)
    has_translation.short_description = _('Translated')
    has_translation.boolean = True

    def set_language(self, request, queryset):
        """
        Set articles selected as published.
        """
        Article.objects.mark_translations(queryset)
        self.message_user(
            request, _('The selected articles are now marked as translations of each other.'))
    set_language.short_description = _('Set articles as translations of each other')


class ArticleTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {'slug': ['name']}


class TaggedArticleAdmin(admin.ModelAdmin):
    raw_id_fields = ('content_object', 'tag')


admin.site.register(Article, ArticleAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(ArticleTag, ArticleTagAdmin)
admin.site.register(TaggedArticle, TaggedArticleAdmin)
