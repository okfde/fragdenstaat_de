from django import template

register = template.Library()


@register.filter
def has_tag(obj, tag_name: str) -> bool:
    return obj.tags.filter(name=tag_name).exists()


@register.filter
def has_all_tags(obj, tag_names: str) -> bool:
    tag_names = [t.strip() for t in tag_names.split(",")]
    if not tag_names:
        return True
    model = obj.tags.through
    return model.objects.filter(
        content_object=obj, tag__name__in=tag_names
    ).count() == len(tag_names)
