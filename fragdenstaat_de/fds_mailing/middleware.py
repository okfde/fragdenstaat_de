from fragdenstaat_de.fds_newsletter.utils import has_newsletter

from .models import EmailTemplate


class EmailTemplateMiddleware:
    def get_email_content(self, mail_intent, context,
                          template_base, email_kwargs):

        email_template = None
        intent = mail_intent
        if template_base is not None:
            try:
                email_template = EmailTemplate.objects.get(
                    active=True, mail_intent=template_base
                )
            except EmailTemplate.DoesNotExist:
                pass
        if email_template is None:
            try:
                email_template = EmailTemplate.objects.get(
                    active=True, mail_intent=intent
                )
            except EmailTemplate.DoesNotExist:
                return
        context = self._enhance_context(context)
        return email_template.get_email_content(context)

    def _enhance_context(self, context):
        if context.get('user'):
            user = context['user']
            context['has_newsletter'] = has_newsletter(user)

        return context
