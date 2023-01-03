import unittest

from cms import api
from cms.api import add_plugin
from cms.test_utils.testcases import CMSTestCase
from djangocms_text_ckeditor.cms_plugins import TextPlugin

MARKER_BEFORE = "MAGIC_MARKER_BEFORE"
MARKER_AFTER = "MAGIC_MARKER_AFTER"


class MiscTests(CMSTestCase):
    @unittest.skip("is flaky")
    def test_text_plugin_nbsp_span(self):
        """
        Regression test: When a span contained only a nbsp, it's content was removed

        We use such spans for formatting, e.g. a span with a user-select: none for spaces in IBANs
        """
        page = api.create_page("TestPage", "cms/home.html", "en")
        ph = page.placeholders.get(slot="content")
        grid_row = add_plugin(
            ph,
            "GridRowPlugin",
            "en",
            config={"vertical_alignment": "auto", "horizontal_alignment": "auto"},
        )
        grid_column = add_plugin(
            ph,
            "GridColumnPlugin",
            "en",
            config={"column_alignment": "auto"},
            target=grid_row,
        )
        add_plugin(
            ph,
            TextPlugin,
            "en",
            body=f"{MARKER_BEFORE}<span>&nbsp;</span>{MARKER_AFTER}",
            target=grid_column,
        )

        page.publish("en")
        page_url = "/en" + page.get_absolute_url()
        staff_user = self.get_staff_user_with_no_permissions()

        with self.login_user_context(staff_user):
            response = self.client.get(page_url)

        self.assertEqual(response.status_code, 200)

        content = response.content.decode()
        model_content_start = content.index(MARKER_BEFORE) + len(MARKER_BEFORE)
        model_content_end = content.index(MARKER_AFTER)
        model_content = content[model_content_start:model_content_end]

        self.assertIn(model_content, ["<span>&nbsp;</span>", "<span>\xa0</span>"])
