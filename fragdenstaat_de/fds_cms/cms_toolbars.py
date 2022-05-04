from django.utils.translation import gettext_lazy as _

from cms.extensions.toolbar import ExtensionToolbar
from cms.toolbar_pool import toolbar_pool

from .models import FdsPageExtension


@toolbar_pool.register
class FdsPageExtensionToolbar(ExtensionToolbar):
    # defines the model for the current toolbar
    model = FdsPageExtension

    def populate(self):
        # setup the extension toolbar with permissions and sanity checks
        current_page_menu = self._setup_extension_toolbar()

        # if it's all ok
        if current_page_menu:
            # retrieves the instance of the current extension (if any) and the toolbar item URL
            page_extension, url = self.get_page_extension_admin()
            if url:
                # adds a toolbar item in position 0 (at the top of the menu)
                current_page_menu.add_modal_item(
                    _("FdS Page Settings"),
                    url=url,
                    disabled=not self.toolbar.edit_mode_active,
                    position=-1,
                )
