from froide.helper.text_utils import convert_html_to_text
from froide.helper.email_sending import send_mail


def add_style(instance, placeholder, context):
    return {
        'style': {
            'primary': '#3676ff',
            'light': '#d0d0d0'
        }
    }


def render_text(instance, placeholder):
    plugins = placeholder.get_plugins()
    return '\n'.join(
        render_plugin_text(plugin) for plugin in plugins
        if plugin.depth == 1
    )


def render_plugin_text(base_plugin):
    instance, plugin = base_plugin.get_plugin_instance()
    if hasattr(plugin, 'render_text'):
        return plugin.render_text(instance)
    if base_plugin.plugin_type == 'TextPlugin':
        return convert_html_to_text(instance.body)
    return ''


def send_template_email(email_template, context, **kwargs):
    content = email_template.get_email_content(context)
    user_email = kwargs.pop('user_email')
    kwargs['html'] = content.html
    return send_mail(
        content.subject, content.text, user_email,
        **kwargs
    )
