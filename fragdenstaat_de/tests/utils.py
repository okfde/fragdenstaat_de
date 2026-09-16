from cms import api as cms_api
from djangocms_versioning.models import Version


def publish_page_content(page, language, user):
    """Publish a page's content for the given language via djangocms-versioning."""
    content = page.pagecontent_set(manager="_original_manager").get(language=language)
    version = Version.objects.get_for_content(content)
    version.publish(user)


def add_language_to_page(page, language, title, user, publish=True, **kwargs):
    """Add a language translation to an existing page, optionally publishing it."""
    cms_api.create_page_content(language, title, page, created_by=user, **kwargs)
    if publish:
        publish_page_content(page, language, user)
