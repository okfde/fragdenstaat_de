from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import (
    EmailActionCMSPlugin, EmailSectionCMSPlugin, EmailStoryCMSPlugin
)
from .utils import render_plugin_text


@plugin_pool.register_plugin
class EmailActionPlugin(CMSPluginBase):
    model = EmailActionCMSPlugin
    module = _("Email")
    name = _("Email Action")
    allow_children = True
    child_classes = ['TextPlugin']
    render_template_template = "email/{name}/action_plugin.html"

    def get_render_template(self, context, instance, placeholder):
        return self.render_template_template.format(
            name=context.get('template') or 'default'
        )

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update(instance.get_context())
        context['instance'] = instance
        return context

    def get_context(self, instance):
        children = instance.get_descendants().order_by('placeholder', 'path')
        text2_children = []
        if children is None:
            text1_children = []
        else:
            text1_children = children
            if len(children) > 1:
                text1_children = children[:-1]
                text2_children = children[-1:]
        return text1_children, text2_children

    def render_text(self, instance):
        text1_children, text2_children = self.get_context(instance)
        text1 = '\n\n'.join(
            render_plugin_text(c) for c in text1_children
        ).strip()
        text2 = '\n\n'.join(
            render_plugin_text(c) for c in text2_children
        ).strip()
        context = instance.get_context()
        context.update({
            'text1': text1,
            'text2': text2,
        })
        return '''{heading}

{text1}

{action_label}
{action_url}
{text2}
'''.format(**context)


@plugin_pool.register_plugin
class EmailSectionPlugin(CMSPluginBase):
    model = EmailSectionCMSPlugin
    module = _("Email")
    name = _("Email Section")
    allow_children = True
    child_classes = ['TextPlugin']
    render_template_template = "email/{name}/section_plugin.html"

    def get_render_template(self, context, instance, placeholder):
        return self.render_template_template.format(
            name=context.get('template') or 'default'
        )

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update(instance.get_context())
        context['instance'] = instance
        return context

    def get_context(self, instance):
        return instance.get_descendants().order_by('placeholder', 'path')

    def render_text(self, instance):
        children = self.get_context(instance)
        text = '\n\n'.join(
            render_plugin_text(c) for c in children
        ).strip()
        context = instance.get_context()
        context.update({
            'text': '\n{}\n\n'.format(text) if text else '',
        })
        return '''## {title}
{text}
'''.format(**context)


@plugin_pool.register_plugin
class EmailStoryPlugin(CMSPluginBase):
    model = EmailStoryCMSPlugin
    module = _("Email")
    name = _("Email Story")
    allow_children = True
    child_classes = ['TextPlugin']
    render_template_template = "email/{name}/story_plugin.html"

    def get_render_template(self, context, instance, placeholder):
        return self.render_template_template.format(
            name=context.get('template') or 'default'
        )

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update(instance.get_context())
        context['instance'] = instance
        return context

    def get_context(self, instance):
        return instance.get_descendants().order_by('placeholder', 'path')

    def render_text(self, instance):
        children = self.get_context(instance)
        text = '\n\n'.join(
            render_plugin_text(c) for c in children
        ).strip()
        context = instance.get_context()
        context.update({
            'text': text
        })
        return '''### {heading}

{text}

-> {url}

'''.format(**context)
