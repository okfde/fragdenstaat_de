from django.shortcuts import get_object_or_404
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from django.views.generic import DateDetailView

from cms.models.pagemodel import Page
from cms.utils.i18n import get_current_language

from froide.helper.breadcrumbs import BreadcrumbView

from fragdenstaat_de.fds_newsletter.models import Newsletter
from fragdenstaat_de.fds_newsletter.utils import has_newsletter

from .models import Mailing


class NewsletterEditionMixin:
    date_field = "sending_date"
    date_list_period = "month"
    allow_empty = True

    year_format = "%Y"
    month_format = "%m"
    day_format = "%d"

    def dispatch(self, *args, **kwargs):
        newsletter_slug = kwargs["newsletter_slug"]
        self.newsletter = get_object_or_404(
            Newsletter.objects.filter(slug=newsletter_slug)
        )
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        return Mailing.published.filter(
            newsletter=self.newsletter,
        )

    def get_context_data(self, **kwargs):
        """Add newsletter to context."""
        context = super().get_context_data(**kwargs)

        context["newsletter"] = self.newsletter

        return context


class MailingArchiveDetailView(NewsletterEditionMixin, DateDetailView, BreadcrumbView):
    template_name = "fds_mailing/archive/mailing_detail.html"

    def get_context_data(self, **kwargs):
        """
        Make sure the actual message is available.
        """
        context = super().get_context_data(**kwargs)

        message = self.object.email_template
        context.update(
            {
                "message": message,
                "content": message.get_body_html(
                    template="fds_mailing/render_browser.html"
                ),
                "date": self.object.sending_date,
                "has_newsletter": has_newsletter(
                    self.request.user, self.object.newsletter
                ),
            }
        )

        return context

    def get_breadcrumbs(self, context):
        try:
            newsletter_url = Page.objects.get(reverse_id="newsletter").get_absolute_url(
                language=get_current_language()
            )
            return [
                (_("Newsletter"), newsletter_url),
                (
                    _("Mailing from %s")
                    % date_format(self.object.sending_date, "DATE_FORMAT")
                ),
            ]
        except Exception:
            return None
