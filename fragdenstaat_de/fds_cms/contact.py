from django import forms
from django.conf.urls import url
from django.core.mail import mail_managers
from django.contrib import messages

try:
    import pgpy
except ImportError:
    pgpy = None

from froide.helper.utils import get_redirect


PUBLIC_KEY = '''
-----BEGIN PGP PUBLIC KEY BLOCK-----

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
p4QEptxo4mIS4QmMjTMX5XI=
=WgO5
-----END PGP PUBLIC KEY BLOCK-----
'''


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        required=False,
        label='Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )

    message = forms.CharField(
        max_length=255,
        required=False,
        label='Nachricht',
        widget=forms.Textarea(attrs={
            'class': 'form-control'
        })
    )

    contact = forms.CharField(
        max_length=255,
        required=False,
        label='Optionale Kontaktmöglichkeit',
        help_text='Zum Beispiel eine private E-Mail-Adresse',
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    # Honey pot field
    url = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.HiddenInput()
    )

    def clean_message(self):
        # Simple spam protection
        if '<a href=' in self.cleaned_data['message']:
            raise forms.ValidationError('')
        return self.cleaned_data['message']

    def clean_url(self):
        # Simple spam protection
        if self.cleaned_data['url']:
            raise forms.ValidationError('')
        return ''

    def send_mail(self):
        text = '''
{name}

{contact}

{message}
        '''.format(
            name=self.cleaned_data['name'],
            contact=self.cleaned_data['contact'],
            message=self.cleaned_data['message'],
        )
        if pgpy is not None:
            public_key = pgpy.PGPKey()
            public_key.parse(PUBLIC_KEY)
            message = pgpy.PGPMessage.new(text)
            text = public_key.encrypt(message)
        mail_managers(
            'Kontaktformular',
            str(text)
        )


def contact(request):
    if request.method == 'POST':
        form = ContactForm(data=request.POST)
        if form.is_valid():
            form.send_mail()
            messages.add_message(
                request, messages.SUCCESS,
                'Wir haben Ihre Nachricht erhalten.'
            )
    return get_redirect(request)


app_name = 'fds_cms_contact'

urlpatterns = [
    url(r'^$', contact, name='contact'),
]
