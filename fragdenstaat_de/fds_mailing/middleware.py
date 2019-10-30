from .models import EmailTemplate


class EmailTemplateMiddleware:
    def get_email_content(self, mail_intent, context,
                          template_base, email_kwargs):

        intent = mail_intent
        if template_base is not None:
            intent = template_base
        try:
            email_template = EmailTemplate.objects.get(
                active=True, mail_intent=intent
            )
        except EmailTemplate.DoesNotExist:
            return
        return email_template.get_email_content(context)
