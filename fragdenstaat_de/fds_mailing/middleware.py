from froide.helper.email_sending import EmailContent

from fragdenstaat_de.fds_newsletter.utils import has_newsletter

from .models import ContinuousMailing, EmailTemplate


class EmailTemplateMiddleware:
    def get_email_content(self, mail_intent, context, template_base, email_kwargs):
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
        if context.get("user"):
            user = context["user"]
            context["has_newsletter"] = has_newsletter(user)

        return context

    def send_mail(
        self,
        mail_intent: str,
        email_content: EmailContent,
        email_address,
        context: dict,
        email_kwargs: dict,
    ):
        try:
            mailing = ContinuousMailing.objects.get(
                email_template__active=True,
                email_template__mail_intent=mail_intent,
                ready=True,
            )
        except ContinuousMailing.DoesNotExist:
            return

        message = mailing.create_message(email_address, context=context)

        # this generates email content a second time but with a different context
        # FIXME: don't generate email content twice
        return message.send(mailing_context=context)
