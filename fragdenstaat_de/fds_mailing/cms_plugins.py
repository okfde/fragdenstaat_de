from django.conf import settings
from django.template import Context, Variable, VariableDoesNotExist
from django.template.loader import TemplateDoesNotExist, get_template
from django.utils.html import format_html, mark_safe
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
from .utils import render_plugin_text, render_plugin_web_html


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

    def render_web_html(self, context, instance):
        children = get_plugin_children(instance)
        return mark_safe(
            "\n\n".join(render_plugin_web_html(context, c) for c in children).strip()
        )


@plugin_pool.register_plugin
class EmailButtonPlugin(EmailTemplateMixin, EmailRenderMixin, CMSPluginBase):
    model = EmailButtonCMSPlugin
    module = _("Email")
    name = _("Email Button")
    allow_children = False
    render_template_template = "email/{name}/button_plugin.html"

    def render(self, context, instance, placeholder):
        instance.attributes.setdefault("color", "#ffffff")
        instance.attributes.setdefault("background-color", "#3676ff")
        return super().render(context, instance, placeholder)

    def render_text(self, context, instance):
        context = instance.get_context()
        return """
{action_label}

{action_url}
""".format(**context)

    def render_web_html(self, context, instance):
        context = instance.get_context()
        style_keys = ["color", "background-color", "border"]
        styles = []
        for key in style_keys:
            if key in instance.attributes:
                styles.append(f"{key}: {instance.attributes[key]}")
        return format_html(
            '<p><a class="btn btn-secondary btn-lg" style="{style}" href="{action_url}">{action_label}</a></p>',
            action_url=context["action_url"],
            action_label=context["action_label"],
            style="; ".join(styles),
        )


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

    def render_web_html(self, context, instance):
        text1_children, text2_children = self.get_context(instance)
        html1 = mark_safe(
            "\n\n".join(
                render_plugin_web_html(context, c) for c in text1_children
            ).strip()
        )
        html2 = mark_safe(
            "\n\n".join(
                render_plugin_web_html(context, c) for c in text2_children
            ).strip()
        )
        context = instance.get_context()
        return format_html(
            "\n".join(
                [
                    "<h3>{heading}</h3>" if context["heading"] else "",
                    "<div>{html1}</div>" if html1 else "",
                    '<p><a class="btn btn-primary btn-lg" href="{action_url}">{action_label}</a><p>',
                    "<div>{html2}</div>" if html2 else "",
                ]
            ),
            heading=context["heading"],
            html1=html1,
            html2=html2,
            action_url=context["action_url"],
            action_label=context["action_label"],
        )


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

    def render_web_html(self, context, instance):
        children = get_plugin_children(instance)
        children_html = mark_safe(
            "\n\n".join(render_plugin_web_html(context, c) for c in children).strip()
        )

        context = instance.get_context()

        return format_html(
            "\n".join(
                [
                    "<h3>{title}</h3>" if context["title"] else "",
                    "<div>{children_html}</div>" if children_html else "",
                ]
            ),
            title=context["title"],
            children_html=children_html,
        )


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

    def render_web_html(self, context, instance):
        children = get_plugin_children(instance)
        children_html = mark_safe(
            "\n\n".join(render_plugin_web_html(context, c) for c in children).strip()
        )

        context = instance.get_context()

        return format_html(
            "\n".join(
                [
                    "<h3>{heading}</h3>" if context["heading"] else "",
                    "<div>{children_html}</div>" if children_html else "",
                    '<p><a class="btn btn-secondary" href="{url}">{label}</a></p>'
                    if context["url"]
                    else "",
                ]
            ),
            heading=context["heading"],
            children_html=children_html,
            url=context["url"],
            label=context["label"],
        )


@plugin_pool.register_plugin
class EmailHeaderPlugin(EmailTemplateMixin, EmailRenderMixin, CMSPluginBase):
    model = EmailHeaderCMSPlugin
    module = _("Email")
    name = _("Email Header")
    allow_children = False
    render_template_template = "email/{name}/header.html"

    def render_text(self, context, instance):
        return ""

    def render_web_html(self, context, instance):
        # TODO: Add support for header?
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
    module = _("Context")
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
        context = Context(context)
        try:
            value = Variable(instance.context_key).resolve(context)
            if instance.context_value:
                comp_value = Variable(instance.context_value).resolve(context)
                result = value == comp_value
            else:
                result = bool(value)
        except VariableDoesNotExist:
            result = False
        if instance.negate:
            result = not result
        return result

    def render_text(self, context, instance):
        if self.should_render(instance, context):
            children = get_plugin_children(instance)
            return "\n\n".join(render_plugin_text(context, c) for c in children).strip()
        return ""

    def render_web_html(self, context, instance):
        if self.should_render(instance, context):
            children = get_plugin_children(instance)
            return mark_safe(
                "\n\n".join(
                    render_plugin_web_html(context, c) for c in children
                ).strip()
            )
        return ""
