from django.shortcuts import get_object_or_404
from django.views.generic import DateDetailView

from fragdenstaat_de.fds_newsletter.models import Newsletter

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
            Newsletter.objects.get_visible().filter(slug=newsletter_slug)
        )
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        return Mailing.objects.filter(
            publish=True,
            ready=True,
            submitted=True,
            sent=True,
            newsletter=self.newsletter,
        )

    def get_context_data(self, **kwargs):
        """Add newsletter to context."""
        context = super().get_context_data(**kwargs)

        context["newsletter"] = self.newsletter

        return context


class MailingArchiveDetailView(NewsletterEditionMixin, DateDetailView):
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
            }
        )

        return context
