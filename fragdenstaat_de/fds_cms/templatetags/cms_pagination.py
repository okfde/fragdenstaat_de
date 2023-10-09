from django import template

register = template.Library()


@register.simple_tag
def get_previous_next_pages(page):
    if page is None:
        return

    parent = page.get_parent_page()
    if parent is None:
        return

    siblings = list(parent.get_child_pages())

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
