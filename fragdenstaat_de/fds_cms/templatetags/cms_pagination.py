from django import template

from cms.utils.i18n import get_current_language

register = template.Library()


@register.simple_tag
def get_previous_next_pages(page):
    if page is None:
        return

    parent = page.get_parent_page()
    if parent is None:
        return

    current_language = get_current_language()
    siblings = [
        page
        for page in parent.get_child_pages()
        if current_language in page.get_languages()
    ]

    current_index = siblings.index(page)
    previous_page = None
    next_page = None

    if current_index > 0:
        previous_page = siblings[current_index - 1]

    if current_index < len(siblings) - 1:
        next_page = siblings[current_index + 1]

    return {
        "previous": previous_page,
        "next": next_page,
    }
