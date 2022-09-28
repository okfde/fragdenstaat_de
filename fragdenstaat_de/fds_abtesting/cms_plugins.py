import random

from django.utils.translation import gettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .forms import ABTestEventForm
from .models import ABTestCMSPlugin, ABTestVariant


@plugin_pool.register_plugin
class ABTestVariantPlugin(CMSPluginBase):
    model = ABTestVariant
    module = _("A/B Test")
    cache = False
    allow_children = True
    render_template = "fds_abtesting/ab_test_variant.html"


@plugin_pool.register_plugin
class ABTestPlugin(CMSPluginBase):
    model = ABTestCMSPlugin
    module = _("A/B Test")
    cache = False
    allow_children = True
    child_classes = ["ABTestVariantPlugin"]
    render_template = "fds_abtesting/ab_test.html"

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        if instance.child_plugin_instances:
            variant = random.choice(instance.child_plugin_instances)
            context["variant"] = variant
            context["form"] = ABTestEventForm(
                initial={"ab_test": instance.ab_test, "variant": str(variant.name)}
            )
        return context
