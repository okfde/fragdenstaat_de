from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.core.cache import cache
from django.urls import reverse
from django.utils.feedgenerator import Enclosure, Rss201rev2Feed
from django.utils.safestring import SafeString, mark_safe
from django.utils.xmlutils import SimplerXMLGenerator

import nh3

from froide.helper.feed_utils import clean_feed_output
from froide.helper.text_utils import convert_html_to_text

from .models import Article, Publication


class CDataSimplerXMLGenerator(SimplerXMLGenerator):
    def characters(self, content):
        if content:
            self._finish_pending_start_element()
            if isinstance(content, SafeString):
                self._write("<![CDATA[{}]]>".format(content))
            else:
                if not isinstance(content, str):
                    content = str(content, self._encoding)
                self._write(escape(content))


class CDataRss201rev2Feed(Rss201rev2Feed):
    def write(self, outfile, encoding):
        # Overwrite Generator, keep rest the same
        handler = CDataSimplerXMLGenerator(outfile, encoding, short_empty_elements=True)
        handler.startDocument()
        handler.startElement("rss", self.rss_attributes())
        handler.startElement("channel", self.root_attributes())
        self.add_root_elements(handler)
        self.write_items(handler)
        self.endChannelElement(handler)
        handler.endElement("rss")


class BaseFeed(Feed):
    protocol = settings.META_SITE_PROTOCOL
    limit = 20
    cache_namespace = "feed"
    feed_type = CDataRss201rev2Feed

    def __call__(self, request, *args, **kwargs):
        cache_key = self.get_cache_key(*args, **kwargs)
        response = cache.get(cache_key)

        if response is None:
            response = super().__call__(request, *args, **kwargs)
            cache.set(cache_key, response, 900)  # cache for 15 minutes

        return response

    def get_cache_key(self, *args, **kwargs):
        # Override this in subclasses for more caching control
        return "%s:%s-%s" % (
            self.cache_namespace,
            self.__class__.__module__,
            "/".join(["%s,%s" % (key, val) for key, val in kwargs.items()]),
        )

    def get_object(self, request):
        # TODO: get the right one from request.app_name
        publication = Publication.objects.all().first()
        return publication

    def title(self, obj=None):
        if obj:
            return obj.title
        return settings.SITE_NAME

    @property
    def site_url(self):
        """
        Return the URL of the current site.
        """
        return settings.SITE_URL

    def link(self):
        return self.site_url

    def description(self, obj=None):
        if obj:
            return obj.description
        return ""

    def item_pubdate(self, item):
        """
        Publication date of an entry.
        """
        return item.start_publication

    def get_queryset(self):
        """
        Items are published entries.
        """
        return Article.published.all()

    @clean_feed_output
    def item_title(self, item):
        if item.kicker:
            return "{}: {}".format(item.kicker, item.title)
        return item.title

    @clean_feed_output
    def item_description(self, item):
        return item.get_full_html_content()


class LatestArticlesFeed(BaseFeed):
    feed_copyright = settings.SITE_NAME

    def item_author_email(self, item):
        """
        Return the first author's email.
        Should not be called if self.item_author_name has returned None.
        """
        return ""

    def items(self):
        """
        Items are published entries.
        """
        queryset = self.get_queryset()
        return queryset[: self.limit]

    def item_link(self, item):
        return self.site_url + item.get_absolute_url()

    def feed_url(self):
        return self.site_url + reverse("blog:article-latest-feed")


class LatestArticlesTeaserFeed(LatestArticlesFeed):
    cache_namespace = "feed-teaser"

    @clean_feed_output
    def item_description(self, obj):
        return convert_html_to_text(obj.description)

    def feed_url(self):
        return self.site_url + reverse("blog:article-latest-feed-teaser")


class PodcastFeed(CDataRss201rev2Feed):
    def __init__(self, *args, **kwargs):
        extra_fields = ("author", "image")
        self.meta = {}
        for field in extra_fields:
            self.meta[field] = kwargs.pop(field, "")
        super().__init__(*args, **kwargs)

    def rss_attributes(self):
        attrs = super().rss_attributes()
        attrs["xmlns:itunes"] = "http://www.itunes.com/dtds/podcast-1.0.dtd"
        attrs["xmlns:content"] = "http://purl.org/rss/1.0/modules/content/"
        return attrs

    def add_root_elements(self, handler):
        super().add_root_elements(handler)
        if self.meta["image"]:
            handler.addQuickElement(
                "itunes:image", None, attrs={"href": self.meta["image"]}
            )
        if self.meta["author"]:
            handler.addQuickElement("itunes:author", self.meta["author"])
        handler.addQuickElement("itunes:explicit", "false")

        # iTunes Category
        handler.startElement("itunes:category", {"text": "News"})
        handler.addQuickElement("itunes:category", None, {"text": "Politics"})
        handler.endElement("itunes:category")

        # iTunes Owner
        handler.startElement("itunes:owner", {})
        handler.addQuickElement("itunes:name", settings.SITE_NAME)
        handler.addQuickElement("itunes:email", settings.SITE_EMAIL)
        handler.endElement("itunes:owner")

    def add_item_elements(self, handler, item):
        """Adds new elements to each item in the feed"""
        super().add_item_elements(handler, item)

        # iTunes Elements
        handler.addQuickElement("itunes:explicit", "false")
        handler.addQuickElement("itunes:author", item["author_name"])
        handler.addQuickElement("itunes:duration", item["audio_duration"])


class LatestAudioFeed(LatestArticlesFeed):
    feed_type = PodcastFeed
    cache_namespace = "feed-audio"

    def feed_url(self):
        return self.site_url + reverse("blog:article-latest-feed-audio")

    def items(self):
        """
        Items are published entries.
        """
        queryset = self.get_queryset().filter(audio__isnull=False)
        return queryset[: self.limit]

    @clean_feed_output
    def item_description(self, item):
        content = item.get_full_html_content()
        content = nh3.clean(content, tags=["p", "ol", "ul", "li", "a"])
        return mark_safe(content)

    def item_enclosures(self, item):
        return [Enclosure(item.audio.url, str(item.audio.size), item.audio.mime_type)]

    def feed_extra_kwargs(self, obj):
        if obj:
            return {
                "author": obj.author,
                "image": obj.image.url if obj.image else None,
            }
        return {
            "author": settings.SITE_NAME,
            "image": None,
        }

    def item_extra_kwargs(self, item):
        return {
            # "image": item.image.url if item.image else None,
            "audio_duration": str(item.audio_duration),
        }
