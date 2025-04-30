from django.conf import settings
from django.template.loader import TemplateDoesNotExist, get_template
from django.utils.translation import gettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from fragdenstaat_de.fds_cms.utils import get_plugin_children

from .models import (
    ConditionCMSPlugin,
    EmailActionCMSPlugin,
    EmailButtonCMSPlugin,
    EmailHeaderCMSPlugin,
    EmailSectionCMSPlugin,
    EmailStoryCMSPlugin,
    Mailing,
    NewsletterArchiveCMSPlugin,
)
from .utils import render_plugin_text


class EmailTemplateMixin:
    def get_render_template(self, context, instance, placeholder):
        template_base = "default"
        obj = context.get("object")
        if obj is not None:
            template_base = obj.template
        template_name = self.render_template_template.format(name=template_base)
        if "{name}" in self.render_template_template and template_base == "mjml":
            template_name = template_name.replace(".html", ".mjml")
        try:
            get_template(template_name)
            return template_name
        except TemplateDoesNotExist:
            pass
        return self.render_template_template.format(name="default")


class EmailRenderMixin:
    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context.update(instance.get_context())
        context["instance"] = instance
        return context


@plugin_pool.register_plugin
class EmailBodyPlugin(EmailTemplateMixin, CMSPluginBase):
    module = _("Email")
    name = _("Email Body")
    render_template_template = "email/{name}/body.html"
    allow_children = True
    child_classes = settings.EMAIL_BODY_PLUGINS

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["instance"] = instance
        return context

    def render_text(self, context, instance):
        children = get_plugin_children(instance)
        return "\n\n".join(render_plugin_text(context, c) for c in children).strip()


@plugin_pool.register_plugin
class EmailButtonPlugin(EmailTemplateMixin, EmailRenderMixin, CMSPluginBase):
    model = EmailButtonCMSPlugin
    module = _("Email")
    name = _("Email Button")
    allow_children = False
    render_template_template = "email/{name}/button_plugin.html"

    def render_text(self, context, instance):
        return """
{action_label}

{action_url}
""".format(**context)


@plugin_pool.register_plugin
class EmailActionPlugin(EmailTemplateMixin, EmailRenderMixin, CMSPluginBase):
    model = EmailActionCMSPlugin
    module = _("Email")
    name = _("Email Action")
    allow_children = True
    child_classes = ["TextPlugin", "PicturePlugin"]
    render_template_template = "email/{name}/action_plugin.html"

    def get_context(self, instance):
        children = list(get_plugin_children(instance))
        text2_children = []
        if children is None:
            text1_children = []
        else:
            text1_children = children
            if len(children) > 1:
                text1_children = children[:-1]
                text2_children = children[-1:]
        return text1_children, text2_children

    def render_text(self, context, instance):
        text1_children, text2_children = self.get_context(instance)
        text1 = "\n\n".join(
            render_plugin_text(context, c) for c in text1_children
        ).strip()
        text2 = "\n\n".join(
            render_plugin_text(context, c) for c in text2_children
        ).strip()
        context = instance.get_context()
        context.update(
            {
                "text1": text1,
                "text2": "\n{}".format(text2) if text2 else "",
            }
        )
        return """{heading}

{text1}

{action_label}
{action_url}
{text2}
""".format(**context)


@plugin_pool.register_plugin
class EmailSectionPlugin(EmailTemplateMixin, EmailRenderMixin, CMSPluginBase):
    model = EmailSectionCMSPlugin
    module = _("Email")
    name = _("Email Section")
    allow_children = True
    child_classes = ["TextPlugin", "PicturePlugin"]
    render_template_template = "email/{name}/section_plugin.html"

    def render_text(self, context, instance):
        children = get_plugin_children(instance)
        text = "\n\n".join(render_plugin_text(context, c) for c in children).strip()
        context = instance.get_context()
        context.update(
            {
                "text": "\n{}\n\n".format(text) if text else "",
            }
        )
        return """## {title}
{text}
""".format(**context)


@plugin_pool.register_plugin
class EmailStoryPlugin(EmailTemplateMixin, EmailRenderMixin, CMSPluginBase):
    model = EmailStoryCMSPlugin
    module = _("Email")
    name = _("Email Story")
    allow_children = True
    child_classes = ["TextPlugin", "PicturePlugin"]
    render_template_template = "email/{name}/story_plugin.html"

    def render_text(self, context, instance):
        children = get_plugin_children(instance)
        text = "\n\n".join(render_plugin_text(context, c) for c in children).strip()
        context = instance.get_context()
        context.update({"text": text})
        return """### {heading}

{text}

-> {url}

""".format(**context)


@plugin_pool.register_plugin
class EmailHeaderPlugin(EmailTemplateMixin, EmailRenderMixin, CMSPluginBase):
    model = EmailHeaderCMSPlugin
    module = _("Email")
    name = _("Email Header")
    allow_children = False
    render_template_template = "email/{name}/header.html"

    def render_text(self, context, instance):
        return ""


@plugin_pool.register_plugin
class NewsletterArchivePlugin(CMSPluginBase):
    model = NewsletterArchiveCMSPlugin
    module = _("Newsletter")
    name = _("Newsletter Archive")
    cache = True
    text_enabled = False
    render_template = "fds_mailing/plugins/archive.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)

        latest_mailings = Mailing.published.filter(
            newsletter=instance.newsletter
        ).order_by("-sending_date")

        if instance.number_of_mailings != 0:
            latest_mailings = latest_mailings[: instance.number_of_mailings]

        context["latest"] = latest_mailings

        return context


@plugin_pool.register_plugin
class ConditionPlugin(CMSPluginBase):
    model = ConditionCMSPlugin
    module = _("Email")
    name = _("Condition")
    allow_children = True
    render_template_template = "email/condition.html"

    def get_render_template(self, context, instance, placeholder):
        return self.render_template_template

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["should_render"] = self.should_render(instance, context)
        return context

    def should_render(self, instance, context):
        value = self.get_context_value(instance, context)
        if instance.context_value:
            result = self.compare_context_value(instance, context, value)
        else:
            result = value is not None
        if instance.negate:
            result = not result
        return result

    def compare_context_value(self, instance, context, value):
        if instance.context_value == "True":
            return value is True
        elif instance.context_value == "False":
            return value is False
        elif instance.context_value == "None":
            return value is None
        else:
            return str(value) == str(instance.context_value)

    def get_context_value(self, instance, context):
        key_list = instance.context_key.split(".")
        for key in key_list:
            try:
                context = context[key]
            except (KeyError, TypeError):
                try:
                    context = getattr(context, key)
                except AttributeError:
                    return None
        return context

    def render_text(self, context, instance):
        if self.should_render(instance, context):
            children = get_plugin_children(instance)
            return "\n\n".join(render_plugin_text(context, c) for c in children).strip()
        return ""
