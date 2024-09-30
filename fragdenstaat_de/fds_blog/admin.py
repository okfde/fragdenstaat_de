from django import forms
from django.contrib import admin
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models import Count
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from adminsortable2.admin import (
    SortableAdminBase,
    SortableAdminMixin,
    SortableInlineAdminMixin,
)
from cms.api import add_plugin
from cms.toolbar.utils import get_object_edit_url
from djangocms_alias.models import Alias
from djangocms_text_ckeditor.widgets import TextEditorWidget
from parler.admin import TranslatableAdmin

from froide.helper.admin_utils import make_choose_object_action, make_nullfilter
from froide.helper.widgets import TagAutocompleteWidget

from .documents import index_article
from .models import (
    Article,
    ArticleAuthorship,
    ArticleTag,
    Author,
    Category,
    LatestArticlesPlugin,
    Publication,
    TaggedArticle,
)


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
        active_objects = (
            self.model.published.all()
            .annotate(count_articles_published=Count("articles"))
            .order_by("-count_articles_published", "-pk")
            .prefetch_related("translations")
        )
        for active_object in active_objects:
            yield (
                str(active_object.pk),
                ngettext_lazy(
                    "%(item)s (%(count)i entry)",
                    "%(item)s (%(count)i articles)",
                    active_object.count_articles_published,
                )
                % {
                    "item": str(active_object),
                    "count": active_object.count_articles_published,
                },
            )

    def queryset(self, request, queryset):
        """
        Return the object's articles if a value is set.
        """
        if self.value():
            params = {self.lookup_key: self.value()}
            return queryset.filter(**params)


class CategoryAdmin(SortableAdminMixin, TranslatableAdmin):
    fields = ("title", "description", "slug", "order", "color", "donation_banner")
    list_display = ("title", "donation_banner")
    search_fields = ("translations__title", "translations__description")
    actions = ["set_donation_banner"]

    def get_prepopulated_fields(self, request, obj=None):
        # can't use `prepopulated_fields = ..` because it breaks the admin validation
        # for translated fields. This is the official django-parler workaround.
        return {"slug": ("title",)}

    set_donation_banner = make_choose_object_action(
        Alias,
        lambda admin, request, qs, obj: qs.update(donation_banner=obj),
        _("Set donation banner..."),
    )


class CategoryListFilter(RelatedPublishedFilter):
    """
    List filter for EntryAdmin about categories
    with published articles.
    """

    model = Category
    lookup_key = "categories__id"
    title = _("published categories")
    parameter_name = "category"


class AuthorAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    actions = ["merge_authors"]

    def merge_authors(self, request, queryset):
        assert len(queryset) >= 1
        author = queryset[0]
        other_authors = list(queryset)[1:]
        for other in other_authors:
            ArticleAuthorship.objects.filter(author=other).update(author=author)
            plugins = LatestArticlesPlugin.objects.filter(authors=other)
            for plugin in plugins:
                plugin.authors.remove(other)
                plugin.authors.add(author)
            other.delete()


class AuthorshipInlineAdmin(SortableInlineAdminMixin, admin.TabularInline):
    model = Article.authors.through
    raw_id_fields = ("author",)


def add_category_on_articles(admin, request, queryset, action_obj):
    for article in queryset:
        article.categories.add(action_obj)


def remove_category_on_articles(admin, request, queryset, action_obj):
    for article in queryset:
        article.categories.remove(action_obj)


class ArticleAdminForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = "__all__"
        widgets = {
            "teaser": TextEditorWidget(),
            "tags": TagAutocompleteWidget(
                autocomplete_url=reverse_lazy("api:articletag-autocomplete")
            ),
        }


class ArticleAdmin(SortableAdminBase, admin.ModelAdmin):
    form = ArticleAdminForm
    date_hierarchy = "start_publication"

    fieldsets = (
        (
            _("Content"),
            {
                "fields": (
                    "title",
                    "kicker",
                    "status",
                    "teaser",
                    "image",
                ),
            },
        ),
        (
            _("URL"),
            {
                "fields": ("slug", "start_publication"),
                "description": _(
                    "Make sure these are correct before publication. Do not change after publication!"
                ),
            },
        ),
        (
            _("Additional Content"),
            {
                "fields": (
                    "categories",
                    "tags",
                    "credits",
                )
            },
        ),
        (
            _("Templates"),
            {
                "fields": ("content_template", "detail_template"),
                "classes": ("collapse", "collapse-closed"),
            },
        ),
        (
            _("Publication Dates"),
            {
                "fields": (("creation_date", "end_publication", "date_featured"),),
                "classes": ("collapse", "collapse-closed"),
            },
        ),
        (
            _("Metadata"),
            {
                "fields": (
                    "excerpt",
                    "related",
                ),
                "classes": ("collapse", "collapse-closed"),
            },
        ),
        (
            _("Audio"),
            {
                "fields": (
                    "audio",
                    "audio_duration",
                ),
                "classes": ("collapse", "collapse-closed"),
            },
        ),
        (
            _("Advanced"),
            {
                "fields": ("language", "uuid", "sites"),
                "classes": ("collapse", "collapse-closed"),
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("title", "slug", "language", "categories"),
            },
        ),
    )
    inlines = (AuthorshipInlineAdmin,)
    list_display = (
        "get_title",
        "get_edit_link",
        "get_authors",
        "get_categories",
        "language",
        "get_is_visible",
        "has_translation",
        "start_publication",
    )

    list_filter = (
        "status",
        CategoryListFilter,
        make_nullfilter("categories", "Hat Kategorie"),
        "tags",
        "date_featured",
        "language",
        make_nullfilter("image", "Hat Bild"),
        "sites",
        "creation_date",
        "start_publication",
        "end_publication",
        make_nullfilter("categories", "Hat Kategorie"),
    )
    radio_fields = {
        "content_template": admin.VERTICAL,
        "detail_template": admin.VERTICAL,
    }
    charcount_fields = ("title", "teaser")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "excerpt", "content", "tags__name")

    raw_id_fields = ("related",)
    filter_horizontal = (
        "categories",
        "authors",
    )
    save_on_top = True

    actions = ["set_language", "add_category", "remove_category"]
    actions_on_top = True

    add_category = make_choose_object_action(
        Category, add_category_on_articles, _("Add category to articles...")
    )

    remove_category = make_choose_object_action(
        Category, remove_category_on_articles, _("Remove category to articles...")
    )

    # def __init__(self, model, admin_site):
    #     # self.form.admin_site = admin_site
    #     super().__init__(model, admin_site)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related(
            "categories",
            "categories__translations",
            "authors",
            "authors__user",
        )
        return qs

    def get_changeform_initial_data(self, request):
        """
        Provide initial datas when creating an entry.
        """
        get_data = super().get_changeform_initial_data(request)
        return get_data or {
            "sites": [Site.objects.get_current().pk],
            "authors": [request.user.pk],
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
            article.content = content or ""

        article.last_update = timezone.now()

        super().save_model(request, article, form, change)

        article.save()

        transaction.on_commit(lambda: index_article(article))

        if not change:
            article.sites.add(Site.objects.get_current())
            blog_content = add_plugin(
                article.content_placeholder, "BlogContent", article.language
            )
            add_plugin(
                article.content_placeholder,
                "TextPlugin",
                article.language,
                body="<p>Content</p>",
                position="first-child",
                target=blog_content,
            )

    def get_title(self, article):
        """
        Return the title with word count and number of comments.
        """
        return article.title

    get_title.short_description = _("title")

    def get_authors(self, article):
        """
        Return the authors in HTML.
        """
        return article.get_authors_string()

    get_authors.short_description = _("author(s)")

    def get_categories(self, article):
        """
        Return the categories linked in HTML.
        """
        categories = [category.title for category in article.categories.all()]
        return ", ".join(categories)

    get_categories.short_description = _("category(s)")

    def get_is_visible(self, article):
        """
        Admin wrapper for article.is_visible.
        """
        return article.is_visible

    get_is_visible.boolean = True
    get_is_visible.short_description = _("is visible")

    def get_edit_link(self, article):
        """
        Return the authors in HTML.
        """
        edit_url = get_object_edit_url(article)
        return format_html(
            '<a href="{url}">{title}</a>',
            url=edit_url,
            title=_("Edit Content"),
        )

    get_edit_link.short_description = _("Content")

    def has_translation(self, article):
        return bool(article.uuid)

    has_translation.short_description = _("Translated")
    has_translation.boolean = True

    def set_language(self, request, queryset):
        """
        Set articles selected as published.
        """
        Article.objects.mark_translations(queryset)
        self.message_user(
            request,
            _("The selected articles are now marked as translations of each other."),
        )

    set_language.short_description = _("Set articles as translations of each other")


class ArticleTagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "articles_count"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(articles_count=Count("articles"))

    @admin.display(description=_("Number of articles"))
    def articles_count(self, obj):
        return obj.articles_count


class TaggedArticleAdmin(admin.ModelAdmin):
    raw_id_fields = ("content_object", "tag")


admin.site.register(Article, ArticleAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(ArticleTag, ArticleTagAdmin)
admin.site.register(TaggedArticle, TaggedArticleAdmin)
admin.site.register(Publication)
