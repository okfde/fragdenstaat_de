from django import template

from djangocms_blog.models import Post

register = template.Library()


@register.filter
def get_next_read(post):
    qs = Post.objects.all()
    if post.date_published:
        return qs.filter(date_published__lt=post.date_published)[0]
    return qs.exclude(pk=post.pk)[0]
