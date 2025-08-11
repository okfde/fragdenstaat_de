import re

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def youtube_url(value) -> str | None:
    # CC BY-SA 3.0 https://stackoverflow.com/a/9102270
    youtube_re = re.compile(
        r".*(youtu\.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*"
    )
    result = re.match(youtube_re, value)

    if result:
        return f"https://www.youtube.com/watch?v={result.group(2)}"
    raise ValueError("Could not parse YouTube URL")
