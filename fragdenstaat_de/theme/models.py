from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from froide.foirequest.hooks import registry


def detect_troll_pre_request_creation(request, **kwargs):
    user = kwargs['user']
    if user.trusted():
        return kwargs

    ip_address = request['REMOTE_ADDR']
    cache_key = 'froide:foirequest:request_per_ip:%s' % ip_address
    count = cache.get_or_set(cache_key, 0)
    try:
        cache.incr(cache_key)
    except ValueError:
        pass
    count += 1

    if user.is_blocked:
        kwargs['blocked'] = True
        return kwargs

    now = timezone.now()
    diff = now - request.user.date_joined
    if (diff < timedelta(days=1) and count > 5) or count > 15:
        request.user.is_blocked = True
        request.user.save()
        kwargs['blocked'] = True

    return kwargs


registry.register('pre_request_creation', detect_troll_pre_request_creation)
