from django import forms

from fragdenstaat_de.fds_cms.contact import ContactForm


class EasylangContactForm(ContactForm):
    page_url = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    def send_mail(self):
        try:
            import pgpy
        except ImportError:
            pgpy = None

        from fragdenstaat_de.fds_cms.contact import PUBLIC_KEY

        text = """
{name}

{contact}

{page_url}

{message}
        """.format(
            name=self.cleaned_data["name"],
            contact=self.cleaned_data["contact"],
            page_url=self.cleaned_data.get("page_url", ""),
            message=self.cleaned_data["message"],
        )
        if pgpy is not None:
            public_key = pgpy.PGPKey()
            public_key.parse(PUBLIC_KEY)
            message = pgpy.PGPMessage.new(text)
            text = public_key.encrypt(message)

        from django.core.mail import mail_managers

        mail_managers("Kontaktformular Leichte Sprache", str(text))
