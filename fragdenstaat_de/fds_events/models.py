from functools import cached_property

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from cms.models import CMSPlugin
from cms.models.fields import PlaceholderRelationField
from cms.utils.placeholder import get_placeholder_from_slot
from filer.fields.image import FilerImageField
from taggit.managers import TaggableManager
from taggit.models import TagBase, TaggedItemBase


class EventManager(models.Manager):
    def get_upcoming(self):
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            self.get_queryset()
            .filter(public=True, end_date__gt=today)
            .order_by("start_date")
        )


class EventTag(TagBase):
    class Meta:
        verbose_name = pgettext_lazy("physical event", "Event Tag")
        verbose_name_plural = pgettext_lazy("physical event", "Event Tags")


class TaggedEvent(TaggedItemBase):
    tag = models.ForeignKey(EventTag, on_delete=models.CASCADE)
    content_object = models.ForeignKey("Event", on_delete=models.CASCADE)

    class Meta:
        verbose_name = pgettext_lazy("physical event", "Tagged Event")
        verbose_name_plural = pgettext_lazy("physical event", "Tagged Events")


class Event(models.Model):
    title = models.CharField(_("Title"), max_length=50)
    slug = models.SlugField(_("Slug"), unique=True)
    description = models.CharField(
        _("Description"),
        help_text=_("Short description, will be shown in the list view"),
        max_length=255,
    )
    start_date = models.DateTimeField(_("Start"))
    end_date = models.DateTimeField(_("End"))
    location = models.CharField(
        _("Location"),
        max_length=255,
        blank=True,
        null=True,
    )
    public = models.BooleanField(default=False)
    placeholders = PlaceholderRelationField()
    tags = TaggableManager(through=TaggedEvent)

    image = FilerImageField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("image"),
        on_delete=models.SET_NULL,
    )

    objects = EventManager()

    class Meta:
        verbose_name = pgettext_lazy("physical event", "Event")
        verbose_name_plural = pgettext_lazy("physical event", "Events")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("fds_events:event-detail", kwargs={"slug": self.slug})

    def get_absolute_domain_url(self):
        return "%s%s" % (settings.SITE_URL, self.get_absolute_url())

    def get_ical_url(self):
        return reverse("fds_events:calendar-event-detail", kwargs={"slug": self.slug})

    @cached_property
    def content_placeholder(self):
        return get_placeholder_from_slot(self.placeholders, "content")

    @property
    def is_event(self):
        # hack to differentiate from lawsuit
        return True

    def get_template(self):
        return "fds_events/placeholder.html"


class NextEventsCMSPlugin(CMSPlugin):
    tags = models.ManyToManyField(
        EventTag,
        help_text=_(
            "Only show events with these tags.",
        ),
        blank=True,
    )
    include_trials = models.BooleanField(
        default=False, help_text=_("Include trials from lawsuits.")
    )
    limit = models.IntegerField(default=0, help_text=_("0 means all events"))
