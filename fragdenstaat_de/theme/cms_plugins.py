from django.utils.translation import ugettext_lazy as _

from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from froide.foirequest.models import FoiRequest
from froide.publicbody.models import PublicBody


@plugin_pool.register_plugin
class ContainerPlugin(CMSPluginBase):
    module = _("Structure")
    name = _("Container")
    render_template = "cms/plugins/container.html"
    allow_children = True


@plugin_pool.register_plugin
class ContainerGreyPlugin(CMSPluginBase):
    module = _("Structure")
    name = _("Container Grey")
    render_template = "cms/plugins/container_grey.html"
    allow_children = True


@plugin_pool.register_plugin
class RowPlugin(CMSPluginBase):
    module = _("Structure")
    name = _("Row")
    render_template = "cms/plugins/row.html"
    allow_children = True


class ColumnPlugin(CMSPluginBase):
    module = _("Structure")
    allow_children = True


# Generate Column Plugin classes and register them
COLUMNS = [
    (3, _('Three')),
    (4, _('Four')),
    (6, _('Six')),
    (8, _('Eight')),
    (9, _('Nine')),
    (12, _('Twelve')),
]

for col_count, col_name in COLUMNS:
    plugin_pool.register_plugin(
        type(
            'Column%sPlugin' % col_count,
            (ColumnPlugin,),
            {
                'name': _("Column " + str(col_name)),
                'render_template': "cms/plugins/col_%d.html" % col_count,
            }
        )
    )


@plugin_pool.register_plugin
class ColumnTeaserPlugin(CMSPluginBase):
    module = _("Structure")
    allow_children = True
    name = _('Column Teaser Three')
    render_template = 'cms/plugins/col_teaser.html'


@plugin_pool.register_plugin
class SubMenuPlugin(CMSPluginBase):
    module = _("Menu")
    name = _("Sub Menu")
    render_template = "cms/plugins/submenu.html"


@plugin_pool.register_plugin
class HomepageHeroPlugin(CMSPluginBase):
    module = _("Homepage")
    name = _("Homepage Hero")
    render_template = "snippets/homepage_hero.html"

    def render(self, context, instance, placeholder):
        context = super(HomepageHeroPlugin, self)\
            .render(context, instance, placeholder)
        context.update({
            'foicount': FoiRequest.objects.get_send_foi_requests().count(),
            'pbcount': PublicBody.objects.get_list().count()
        })
        return context


@plugin_pool.register_plugin
class HomepageHowPlugin(CMSPluginBase):
    module = _("Homepage")
    name = _("Homepage How")
    render_template = "snippets/homepage_how.html"
