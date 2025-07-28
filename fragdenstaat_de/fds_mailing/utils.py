import base64
import re
from datetime import timedelta
from urllib.parse import parse_qs, urlencode, urlparse

from django.conf import settings
from django.contrib.admin import helpers
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.crypto import salted_hmac
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _

from froide.helper.email_sending import send_mail
from froide.helper.forms import get_fake_fk_form_class
from froide.helper.text_utils import convert_html_to_text

EMPTY_PARAGRAPH = re.compile(r"<p>(\s|&nbsp;)*</p>")


def add_style(instance, placeholder, context):
    return {"style": {"primary": "#3676ff", "light": "#d0d0d0"}}


def render_text(placeholder, context):
    plugins = placeholder.get_plugins()
    return "\n".join(
        render_plugin_text(context, plugin) for plugin in plugins if not plugin.parent
    )


def render_web_html(placeholder, context):
    plugins = placeholder.get_plugins()
    return "\n".join(
        render_plugin_web_html(context, plugin)
        for plugin in plugins
        if not plugin.parent
    )


def render_plugin_web_html(context, base_plugin):
    instance, plugin = base_plugin.get_plugin_instance()
    if instance is None:
        return ""
    if hasattr(plugin, "render_web_html"):
        return plugin.render_web_html(context, instance)
    if base_plugin.plugin_type == "TextPlugin":
        return mark_safe(EMPTY_PARAGRAPH.sub("", instance.body))
    elif base_plugin.plugin_type == "PicturePlugin":
        # TODO
        context = plugin.render(context, instance, None)
        return render_to_string(
            "djangocms_picture/default/picture.html",
            context,
        )
    return ""


def render_plugin_text(context, base_plugin):
    instance, plugin = base_plugin.get_plugin_instance()
    if instance is None:
        return ""
    if hasattr(plugin, "render_text"):
        return plugin.render_text(context, instance)
    if base_plugin.plugin_type == "TextPlugin":
        return convert_html_to_text(instance.body, ignore_tags=("b", "strong"))
    return ""


def send_template_email(email_template, context, **kwargs):
    content = email_template.get_email_content(context)
    user_email = kwargs.pop("user_email")
    kwargs["html"] = content.html
    return send_mail(content.subject, content.text, user_email, **kwargs)


def get_admin_url(obj):
    return reverse(
        "admin:%s_%s_change" % (obj._meta.app_label, obj._meta.model_name),
        args=[obj.pk],
    )


class SetupMailingMixin:
    actions = ["setup_mailing"]

    def setup_mailing_messages(self, mailing, queryset):
        raise NotImplementedError

    def setup_mailing(self, request, queryset):
        from .models import EmailTemplate, Mailing

        opts = self.model._meta
        # Check that the user has change permission for the actual model
        if not self.has_change_permission(request):
            raise PermissionDenied

        Form = get_fake_fk_form_class(EmailTemplate, self.admin_site)
        # User has already chosen the other req
        if request.POST.get("obj"):
            f = Form(request.POST)
            if f.is_valid():
                email_template = f.cleaned_data["obj"]

                mailing = Mailing.objects.create(
                    name=email_template.name,
                    creator_user=request.user,
                    email_template=email_template,
                )

                message = self.setup_mailing_messages(mailing, queryset)

                self.message_user(request, message)

                return redirect(get_admin_url(mailing))
        else:
            f = Form()

        context = {
            "opts": opts,
            "queryset": queryset,
            "media": self.media,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "form": f,
            "applabel": opts.app_label,
        }

        # Display the confirmation page
        return TemplateResponse(
            request, "admin/fds_mailing/mailing/send_mailing.html", context
        )

    setup_mailing.short_description = _("Prepare mailing to selected recipients...")


def handle_bounce(sender, bounce, should_deactivate=False, **kwargs):
    from .models import MailingMessage

    sent_after = bounce.last_update - timedelta(hours=36)
    MailingMessage.objects.filter(
        sent__isnull=False, sent__gte=sent_after, email=bounce.email
    ).update(bounced=True)


def add_fake_context(context, intent):
    if intent is None:
        return context

    from froide.foirequest.models import FoiRequest

    from fragdenstaat_de.fds_donation.models import Donation, Donor

    USER_FAKERS = {
        "user": lambda u: u,
        "foirequest": lambda u: FoiRequest.objects.filter(user=u)[0],
        "publicbody": lambda u: FoiRequest.objects.filter(user=u)[0].public_body,
        "public_body": lambda u: FoiRequest.objects.filter(user=u)[0].public_body,
        "donor": lambda u: Donor.objects.filter(user=u)[0],
        "name": lambda u: Donor.objects.filter(user=u)[0].get_full_name(),
        "first_name": lambda u: Donor.objects.filter(user=u)[0].first_name,
        "last_name": lambda u: Donor.objects.filter(user=u)[0].last_name,
        "salutation": lambda u: Donor.objects.filter(user=u)[0].get_salutation(),
        "donation": lambda u: Donation.objects.filter(donor__user=u)[0],
        "payment": lambda u: Donation.objects.filter(donor__user=u)[0].payment,
        "order": lambda u: Donation.objects.filter(donor__user=u)[0].order,
        "action_url": lambda u: settings.SITE_URL,
    }

    context_vars = []
    context_vars.extend(intent.context_vars)
    context_vars.extend(intent.get_context({}, preview=True).keys())
    request = context["request"]
    user = request.user
    for var in context_vars:
        if var in context:
            continue
        if var in USER_FAKERS:
            context[var] = USER_FAKERS[var](user)

    return context


def b32_encode(s: bytes) -> bytes:
    return base64.b32encode(s).strip(b"=")


def base32_hmac(salt, value, key, algorithm="sha1") -> str:
    return b32_encode(
        salted_hmac(salt, value, key, algorithm=algorithm).digest()
    ).decode()


class LowerCaseSigner(signing.Signer):
    def signature(self, value, key=None):
        key = key or self.key
        return base32_hmac(
            self.salt + "signer", value, key, algorithm=self.algorithm
        ).lower()


def get_url_tagger(mailing_campaign: str, query_param: str = "pk_campaign") -> str:
    url_regex = re.compile('(%s[^\\s"]+)' % re.escape(settings.SITE_URL))

    def tag_urls(text, html_entities=False):
        def replace_match(match):
            url_match = match.group(1)
            if html_entities:
                url_match = url_match.replace("&amp;", "&")
            url = urlparse(url_match)
            qs = parse_qs(url.query)
            if query_param in qs:
                return match.group(0)
            qs[query_param] = [mailing_campaign]
            url_str = url._replace(query=urlencode(qs, doseq=True)).geturl()
            if html_entities:
                url_str = url_str.replace("&", "&amp;")
            return url_str

        return url_regex.sub(replace_match, text)

    return tag_urls
