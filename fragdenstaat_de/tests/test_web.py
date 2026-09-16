from django.test import TestCase

from fragdenstaat_de.tests.utils import reload_urls


class TestWebAppsForm(TestCase):
    fixtures = ["cms.json"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addClassCleanup(reload_urls)
        reload_urls()

    def test_homepage(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_blog(self):
        response = self.client.get("/artikel/")
        self.assertEqual(response.status_code, 200)

    def test_legacy_blog_redirect(self):
        response = self.client.get("/blog/")
        self.assertRedirects(
            response, "/artikel/", status_code=301, fetch_redirect_response=False
        )

    def test_cms_search(self):
        response = self.client.get("/hilfe/suche/")
        self.assertEqual(response.status_code, 200)

    def test_crowdfunding(self):
        response = self.client.get("/crowdfunding/edit/")
        self.assertEqual(response.status_code, 302)

    def test_food(self):
        response = self.client.get("/food/")
        self.assertEqual(response.status_code, 200)

    def test_exam(self):
        response = self.client.get("/exam/")
        self.assertEqual(response.status_code, 302)
