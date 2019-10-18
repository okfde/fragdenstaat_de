import base64
import json

from django import forms
from django.core.mail import mail_managers
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.conf import settings

from froide.account.utils import parse_address
from froide.helper.content_urls import get_content_url
from froide.campaign.models import Campaign

from froide_payment.models import CHECKOUT_PAYMENT_CHOICES_DICT
from froide_payment.forms import StartPaymentMixin
from froide_payment.utils import interval_description

from .models import DonationGift, INTERVAL_SETTINGS_CHOICES
from .widgets import AmountInput, InlineRadioSelect


CROWDFUNDING_METHODS = (
    'creditcard', 'lastschrift', 'paypal', 'sofort'
)

PAYMENT_METHODS = [
    (method, CHECKOUT_PAYMENT_CHOICES_DICT[method])
    for method in CROWDFUNDING_METHODS
]


class DonationSettingsForm(forms.Form):
    interval = forms.ChoiceField(
        choices=INTERVAL_SETTINGS_CHOICES,
    )
    amount_presets = forms.RegexField(
        regex=r'\d+(?:,\d+)*',
    )
    reference = forms.CharField(
        required=False
    )

    def clean_amount_presets(self):
        presets = self.cleaned_data['amount_presets']
        if '[' in presets:
            presets = presets.replace('[', '').replace(']', '')
        return [int(x.strip()) for x in presets.split(',')]

    def make_donation_form(self, **kwargs):
        d = {}
        if self.is_valid():
            d = self.cleaned_data
        return DonationFormFactory(**d).make_form(**kwargs)


class DonationFormFactory:
    default = {
        'interval': 'once_recurring',
        'reference': '',
        'amount_presets': [5, 20, 50],
        'initial_amount': None,
        'initial_interval': 0,
        'initial_receipt': '0',
    }
    initials = {
        'initial_amount': 'amount',
        'initial_interval': 'interval',
        'initial_receipt': 'receipt'
    }

    def __init__(self, **kwargs):
        self.settings = {}
        for key in self.default:
            self.settings[key] = kwargs.get(key, self.default[key])

    def make_form(self, **kwargs):
        if 'data' in kwargs:
            form_settings = kwargs['data'].get('form_settings')
            raw_data = self.deserialize(form_settings)
            settings_form = DonationSettingsForm(data=raw_data)
            if settings_form.is_valid():
                self.settings.update(settings_form.cleaned_data)

        kwargs.setdefault('initial', {})
        kwargs['initial']['form_settings'] = self.serialize()
        for k, v in self.initials.items():
            kwargs['initial'][v] = self.settings[k]

        kwargs['form_settings'] = self.settings

        return DonationForm(**kwargs)

    def serialize(self):
        return base64.b64encode(json.dumps(self.settings).encode('utf-8')).decode('utf-8')

    def deserialize(self, encoded):
        if encoded is None:
            return self.default
        try:
            decoded_bytes = base64.b64decode(encoded)
        except ValueError:
            return self.default
        try:
            unicode_str = decoded_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return self.default
        try:
            raw_data = json.loads(unicode_str)
        except ValueError:
            return self.default
        return raw_data


class AmountForm(forms.Form):
    amount = forms.DecimalField(
        localize=True,
        required=True,
        initial=None,
        min_value=5,
        max_digits=19,
        decimal_places=2,
        label=_('Amount'),
        widget=AmountInput(
            attrs={
                'autocomplete': 'off',
                'title': _('Amount in Euro, comma as decimal separator'),
                'pattern': '^[1-9]{1}\d{0,4}(?:,\d\d)?$',
            },
            presets=[]
        )
    )
    interval = forms.TypedChoiceField(
        choices=[],
        coerce=int,
        empty_value=None,
        required=True,
        label=_('Frequency'),
        widget=InlineRadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    reference = forms.ChoiceField(
        required=False,
        label=_('Donation reference'),
        choices=[
            ('', 'Allgemeine Spende'),
        ],
        widget=forms.Select(
            attrs={
                'data-toggle': "nonrecurring",
                'class': 'form-control'
            },
        )
    )
    payment_method = forms.ChoiceField(
        label=_('Payment method'),
        choices=PAYMENT_METHODS,
        widget=forms.RadioSelect(attrs={
            'class': 'list-unstyled'
        }),
        initial=PAYMENT_METHODS[0][0]
    )


class DonorForm(forms.Form):
    salutation = forms.ChoiceField(
        label=_('Salutation'),
        required=True,
        choices=(
            ('', '----'),
            ('Frau', 'Frau'),
            ('Herr', 'Herr'),
            ('-', 'Divers'),
        ),
        widget=forms.Select(attrs={
            'class': "form-control"
        })
    )
    first_name = forms.CharField(
        max_length=255,
        label=_('First name'),
        widget=forms.TextInput(attrs={
            'placeholder': _('First name'),
            'class': 'form-control'
        })
    )
    last_name = forms.CharField(
        max_length=255,
        label=_('Last name'),
        widget=forms.TextInput(attrs={
            'placeholder': _('Last name'),
            'class': 'form-control'
        })
    )
    company = forms.CharField(
        label=_('Company'),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Company name')
            }
        ))

    receipt = forms.TypedChoiceField(
        widget=InlineRadioSelect(attrs={
            'class': 'form-check-input',
            'data-toggle': 'radiocollapse',
            'data-target': 'address-fields'
        }),
        choices=(
            (0, _('No, thank you.')),
            (1, _('Yes, once a year.')),
        ),
        coerce=lambda x: bool(int(x)),
        required=True,
        label=_('Do you want a donation receipt?'),
        error_messages={
            'required': _('You have to decide.')
        },
    )
    address = forms.CharField(
        max_length=255,
        label=_('Street, house number'),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _('Street, house number'),
            'class': 'form-control'
        })
    )
    postcode = forms.CharField(
        max_length=255,
        label=_('Postcode'),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _('Postcode'),
            'class': 'form-control'
        })
    )
    city = forms.CharField(
        max_length=255,
        label=_('City'),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _('City'),
            'class': 'form-control'
        })
    )
    country = forms.ChoiceField(
        label=_('Country'),
        required=False,
        choices=(
            ('DE', _('Germany')),
            ('AT', _('Austria')),
            ('CH', _('Switzerland')),
        ),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        label=_('Email'),
        required=True,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('e.g. name@example.org')
            }
        ))


class DonationForm(StartPaymentMixin, AmountForm, DonorForm):
    form_settings = forms.CharField(
        widget=forms.HiddenInput)
    contact = forms.TypedChoiceField(
        widget=forms.RadioSelect(attrs={
            'class': 'list-unstyled'
        }),
        choices=(
            (1, _('Yes, please!')),
            (0, _('No, thank you.')),
        ),
        coerce=lambda x: bool(int(x)),
        required=True,
        label=_('News'),
        error_messages={
            'required': _('You have to decide.')
        },
    )
    account = forms.TypedChoiceField(
        widget=forms.RadioSelect(attrs={
            'class': 'list-unstyled'
        }),
        choices=(),
        coerce=lambda x: bool(int(x)),
        required=True,
        label=_('With your donation you can also create a '
            'FragDenStaat account where you can manage your '
            'details, donations and requests.'
        ),
        error_messages={
            'required': _('You have to decide.')
        },
    )

    def __init__(self, *args, **kwargs):
        self.action = kwargs.pop('action', None)

        user = kwargs.pop('user', None)
        if not user.is_authenticated:
            user = None
        self.user = user
        self.settings = kwargs.pop(
            'form_settings',
            DonationFormFactory.default
        )

        super().__init__(*args, **kwargs)
        if self.user is not None:
            self.fields['email'].initial = self.user.email
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            parsed = parse_address(self.user.address)
            self.fields['address'].initial = parsed.get('address', '')
            self.fields['postcode'].initial = parsed.get('postcode', '')
            self.fields['city'].initial = parsed.get('city', '')
            self.fields.pop('account')
        else:
            self.fields['account'].choices = (
                (1, format_html(
                    'Ja, super praktisch. Ich stimme den <a href="{url_terms}" target="_blank">'
                    'Nutzungsbedingungen</a> zu.',
                    url_terms=get_content_url("terms"),
                )),
                (0, _('No, thank you.')),
            )

        interval_choices = []
        if 'once' in self.settings['interval']:
            interval_choices.append(('0', _('once')),)
        else:
            # No once option -> not choosing reference
            self.fields['reference'].widget = forms.HiddenInput()
        if 'recurring' in self.settings['interval']:
            interval_choices.extend([
                ('1', _('monthly')),
                ('3', _('quarterly')),
                ('12', _('yearly')),
            ])
        self.fields['interval'].choices = interval_choices
        if len(interval_choices) == 1:
            self.fields['interval'].widget = forms.HiddenInput()
        self.fields['amount'].widget.presets = self.settings['amount_presets']

        if self.settings['reference']:
            self.fields['reference'].initial = self.settings['reference']
            self.fields['reference'].widget = forms.HiddenInput()
        else:
            self.fields['reference'].widget.choices.extend([
                (x.slug, x.name) for x in Campaign.objects.get_filter_list()
            ])

    def get_payment_metadata(self, data):
        if data['interval'] > 0:
            return {
                'category': _('Donation for %s') % settings.SITE_NAME,
                'plan_name': _('{amount} EUR donation {str_interval} to {site_name}').format(
                    amount=data['amount'],
                    str_interval=interval_description(data['interval']),
                    site_name=settings.SITE_NAME
                ),
                'description': settings.SITE_NAME,
                'kind': 'fds_donation.Donation',
            }
        else:
            return {
                'category': _('Donation for %s') % settings.SITE_NAME,
                'description': settings.SITE_NAME,
                'kind': 'fds_donation.Donation',
            }

    def create_related_object(self, order, data):
        pass
        # Create donor/donation donation
        # contribution = Contribution.objects.create(
        #     crowdfunding=self.crowdfunding,
        #     user=self.user,
        #     amount=self.cleaned_data['amount'],
        #     note=self.cleaned_data.get('note', ''),
        #     public=self.cleaned_data.get('public', False),
        #     order=order,
        # )

    def save(self):
        data = self.cleaned_data
        data['is_donation'] = True
        order = self.create_order(data)
        related_obj = self.create_related_object(order, data)

        return order, related_obj


class DonationGiftForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        label=_('Your name'),
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        max_length=255,
        label=_('Your email address'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control'
        })
    )
    gift = forms.ModelChoiceField(
        label=_('Please choose your donation gift'),
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
