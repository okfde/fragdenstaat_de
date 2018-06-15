from datetime import timedelta
from urllib.parse import urlencode

from django.shortcuts import redirect
from django.core.cache import cache
from django.utils import timezone
from django.core.mail import mail_managers
from django.utils.translation import ugettext_lazy as _

from froide.foirequest.hooks import registry


def detect_troll_pre_request_creation(request, **kwargs):
    user = kwargs['user']
    if user.trusted():
        return kwargs

    ip_address = request.META['REMOTE_ADDR']
    cache_key = 'froide:foirequest:request_per_ip:%s' % ip_address
    count = cache.get(cache_key, 0)
    if count == 0:
        cache.set(cache_key, 1)
    else:
        try:
            cache.incr(cache_key)
        except ValueError:
            pass
    count += 1

    if user.is_blocked:
        kwargs['blocked'] = True
        return kwargs

    now = timezone.now()
    diff = now - user.date_joined
    if (diff < timedelta(days=1) and count > 5) or count > 15:
        user.is_blocked = True
        user.save()
        mail_managers(_('User blocked'), str(user.pk))
        kwargs['blocked'] = True

    return kwargs

# Uncomment to activate troll filter again
# registry.register('pre_request_creation', detect_troll_pre_request_creation)


def inject_status_change(request, **kwargs):
    data = kwargs['data']
    foirequest = data['foirequest']
    form = data['form']
    data = form.cleaned_data
    if data['resolution'] in ('successful', 'partially_successful'):
        next_url = foirequest.get_absolute_url()
        params = urlencode({'next': next_url})
        return redirect('/spenden/erfolgreiche-anfrage/?' + params)


registry.register('post_status_set', inject_status_change)
