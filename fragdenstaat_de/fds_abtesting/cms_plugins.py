import random

from django.utils.translation import gettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool


@plugin_pool.register_plugin
class ABTestPlugin(CMSPluginBase):
    module = _("A/B Test")
    cache = False
    allow_children = True
    render_template = "fds_abtesting/ab_test.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["random_plugin"] = random.choice(instance.child_plugin_instances)
        return context
