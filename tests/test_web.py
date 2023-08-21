import unittest

from django.test import TestCase


class TestWebAppsForm(TestCase):
    fixtures = ["cms.json"]

    def test_homepage(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_blog(self):
        response = self.client.get("/blog/")
        self.assertEqual(response.status_code, 200)

    @unittest.skip("Search needs to be setup as CMS app")
    def test_cms_search(self):
        # Currently not working because for testing
        # this is not setup as CMS app, but hooked directly.
        # Template now depends on request.current_page
        # being available
        response = self.client.get("/cms/search/")
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
