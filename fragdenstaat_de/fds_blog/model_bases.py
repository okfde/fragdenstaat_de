"""Modified Base entry models from Django Blog Zinnia"""

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import models
from django.utils import timezone
from django.utils.html import linebreaks, strip_tags
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from filer.fields.file import FilerFileField

from .managers import DRAFT, HIDDEN, PUBLISHED


class CoreEntry(models.Model):
    """
    Abstract core entry model class providing
    the fields and methods required for publishing
    content over time.
    """

    STATUS_CHOICES = (
        (DRAFT, _("draft")),
        (HIDDEN, _("hidden")),
        (PUBLISHED, _("published")),
    )

    title = models.CharField(_("title"), max_length=255)

    slug = models.SlugField(
        _("slug"),
        max_length=255,
        unique_for_date="start_publication",
        help_text=_("Used to build the entry's URL."),
    )

    status = models.IntegerField(
        _("status"), db_index=True, choices=STATUS_CHOICES, default=DRAFT
    )

    start_publication = models.DateTimeField(
        _("start publication"),
        db_index=True,
        default=timezone.now,
        help_text=_("Start date of publication. Used to build the entry's URL."),
    )

    end_publication = models.DateTimeField(
        _("end publication"),
        db_index=True,
        blank=True,
        null=True,
        help_text=_("End date of publication."),
    )

    sites = models.ManyToManyField(
        Site,
        related_name="articles",
        verbose_name=_("sites"),
        help_text=_("Sites where the article will be published."),
    )

    creation_date = models.DateTimeField(
        _("creation date"),
        db_index=True,
        default=timezone.now,
    )

    last_update = models.DateTimeField(_("last update"), default=timezone.now)

    class Meta:
        abstract = True

    @property
    def publication_date(self):
        """
        Return the publication date of the entry.
        """
        return self.start_publication or self.creation_date

    @property
    def is_actual(self):
        """
        Checks if an entry is within his publication period.
        """
        now = timezone.now()
        if self.start_publication and now < self.start_publication:
            return False

        if self.end_publication and now >= self.end_publication:
            return False
        return True

    @property
    def is_visible(self):
        """
        Checks if an entry is visible and published.
        """
        return self.is_actual and self.status == PUBLISHED

    def save(self, *args, **kwargs):
        """
        Overrides the save method to update the
        the last_update field.
        """
        self.last_update = timezone.now()
        super(CoreEntry, self).save(*args, **kwargs)


class ContentEntry(models.Model):
    """
    Abstract content model class providing field
    and methods to write content inside an entry.
    """

    content = models.TextField(_("content"), blank=True)

    @property
    def html_content(self):
        """
        Returns the "content" field formatted in HTML.
        """
        content = self.content
        if not content:
            return ""
        return content

    @property
    def word_count(self):
        """
        Counts the number of words used in the content.
        """
        return len(strip_tags(self.html_content).split())

    class Meta:
        abstract = True


class RelatedEntry(models.Model):
    """
    Abstract model class for making manual relations
    between the differents entries.
    """

    related = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name=_("related articles"),
        help_text=_("You can link articles here that are part of a series."),
    )

    class Meta:
        abstract = True


class LeadEntry(models.Model):
    """
    Abstract model class providing a lead content to the entries.
    """

    lead = models.TextField(_("lead"), blank=True, help_text=_("Lead paragraph"))

    @property
    def html_lead(self):
        """
        Returns the "lead" field formatted in HTML.
        """
        if self.lead:
            return linebreaks(self.lead)
        return ""

    class Meta:
        abstract = True


class ExcerptEntry(models.Model):
    """
    Abstract model class to add an excerpt to the entries.
    """

    excerpt = models.TextField(
        _("excerpt"), blank=True, help_text=_("Used for SEO purposes.")
    )

    def save(self, *args, **kwargs):
        """
        Overrides the save method to create an excerpt
        from the content field if void.
        """
        if not self.excerpt and self.status == PUBLISHED:
            self.excerpt = Truncator(strip_tags(getattr(self, "content", ""))).words(50)
        super(ExcerptEntry, self).save(*args, **kwargs)

    class Meta:
        abstract = True


class ContentTemplateEntry(models.Model):
    """
    Abstract model class to display entry's content
    with a custom template.
    """

    content_template = models.CharField(
        _("content template"),
        max_length=250,
        default="fds_blog/_article_detail.html",
        choices=[("fds_blog/_article_detail.html", _("Default template"))]
        + settings.ARTICLE_CONTENT_TEMPLATES,
        help_text=_("Template used to display the article's content."),
    )

    class Meta:
        abstract = True


class DetailTemplateEntry(models.Model):
    """
    Abstract model class to display entries with a
    custom template if needed on the detail page.
    """

    detail_template = models.CharField(
        _("detail template"),
        max_length=250,
        default="fds_blog/article_detail.html",
        choices=[("fds_blog/article_detail.html", _("Default template"))]
        + settings.ARTICLE_DETAIL_TEMPLATES,
        help_text=_("Template used to display the article's detail page."),
    )

    class Meta:
        abstract = True


class AudioEntry(models.Model):
    """
    Abstract model class to display entries with a
    custom template if needed on the detail page.
    """

    audio = FilerFileField(
        null=True,
        blank=True,
        default=None,
        verbose_name=_("audio file"),
        on_delete=models.SET_NULL,
        related_name="audio_articles",
    )
    audio_duration = models.IntegerField(
        null=True, blank=True, verbose_name=_("duration in seconds")
    )

    class Meta:
        abstract = True
