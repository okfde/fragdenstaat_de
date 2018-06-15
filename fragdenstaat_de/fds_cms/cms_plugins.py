from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from froide.helper.utils import get_redirect_url

from .models import (
    PageAnnotationCMSPlugin, DocumentPagesCMSPlugin,
    PrimaryLinkCMSPlugin
)


@plugin_pool.register_plugin
class PageAnnotationPlugin(CMSPluginBase):
    model = PageAnnotationCMSPlugin
    module = _("Document")
    name = _("Page Annotation")
    text_enabled = True
    render_template = "document/cms_plugins/page_annotation.html"
    raw_id_fields = ('page_annotation',)

    def render(self, context, instance, placeholder):
        context = super(PageAnnotationPlugin, self)\
            .render(context, instance, placeholder)

        context['object'] = instance.page_annotation

        return context


@plugin_pool.register_plugin
class DocumentPagesPlugin(CMSPluginBase):
    model = DocumentPagesCMSPlugin
    module = _("Document")
    name = _("Document pages")
    text_enabled = True
    render_template = "document/cms_plugins/document_pages.html"
    raw_id_fields = ('doc',)

    def render(self, context, instance, placeholder):
        context = super(DocumentPagesPlugin, self)\
            .render(context, instance, placeholder)

        context['object'] = instance
        context['pages'] = instance.get_pages()

        return context


@plugin_pool.register_plugin
class PrimaryLinkPlugin(CMSPluginBase):
    module = _("Elements")
    name = _('Primary Link')
    default_template = "cms/plugins/primarylink/default.html"
    model = PrimaryLinkCMSPlugin

    def get_render_template(self, context, instance, placeholder):
        if instance.template:
            return instance.template
        return self.default_template

    def render(self, context, instance, placeholder):
        context = super(PrimaryLinkPlugin, self)\
            .render(context, instance, placeholder)
        context['object'] = instance
        return context


@plugin_pool.register_plugin
class ContinueLinkPlugin(CMSPluginBase):
    module = _("Elements")
    name = _('Continue Link')
    text_enabled = True
    cache = False
    render_template = "cms/plugins/continue_link.html"

    def render(self, context, instance, placeholder):
        context = super(ContinueLinkPlugin, self)\
            .render(context, instance, placeholder)
        request = context['request']
        context['title'] = request.GET.get('next_title', 'Weiter zu Ihrer Anfrage')
        next_url = get_redirect_url(request)
        context['next_url'] = next_url
        return context
