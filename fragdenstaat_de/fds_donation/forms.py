from django import forms
from django.core.mail import mail_managers

from .models import DonationGift


class DonationGiftForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        label='Ihr Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        max_length=255,
        label='Ihre E-Mail-Adresse',
        widget=forms.EmailInput(attrs={
            'class': 'form-control'
        })
    )
    gift = forms.ModelChoiceField(
        label='Wählen Sie Ihr Dankeschön aus',
        queryset=None
    )

    def __init__(self, *args, **kwargs):
        self.category = kwargs.pop('category')
        super().__init__(*args, **kwargs)
        self.fields['gift'].queryset = DonationGift.objects.filter(
            category_slug=self.category
        )

    def save(self, request=None):
        text = [
            'Name', self.cleaned_data['name'],
            'E-Mail', self.cleaned_data['email'],
            'Auswahl', self.cleaned_data['gift'],
        ]
        if request and request.user:
            text.extend([
                'User', request.user.id
            ])

        mail_managers(
            'Neue Bestellung von %s' % self.category,
            str('\n'.join(str(t) for t in text))
        )
