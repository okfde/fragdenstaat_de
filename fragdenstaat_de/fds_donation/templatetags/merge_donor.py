from django import template

register = template.Library()


@register.filter
def get_field_by_key(obj, key=None):
    if key is None:
        return
    return getattr(obj, key)
