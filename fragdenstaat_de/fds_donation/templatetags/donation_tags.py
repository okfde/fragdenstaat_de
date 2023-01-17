from django import template
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from dateutil.relativedelta import relativedelta

from ..models import Donor

register = template.Library()

ACTIVE_TIME = relativedelta(months=24)
SLEEPING_TIME = relativedelta(months=36)


@register.inclusion_tag("fds_donation/stats/admin_dashboard.html", takes_context=True)
def donor_type_counts(context):
    now = timezone.now()

    active_filter = Q(last_donation__gte=now - ACTIVE_TIME)
    sleeping_filter = Q(last_donation__lt=now - ACTIVE_TIME) & Q(
        last_donation__gte=now - SLEEPING_TIME
    )
    inactive_filter = Q(last_donation__lt=now - SLEEPING_TIME)

    aggs = Donor.objects.annotate(
        last_donation=Max(
            "donations__timestamp",
            filter=Q(donations__received_timestamp__isnull=False),
        )
    ).aggregate(
        active_count=Count("id", filter=active_filter),
        sleeping_count=Count("id", filter=sleeping_filter),
        inactive_count=Count("id", filter=inactive_filter),
    )
    return {"aggs": aggs}


@register.inclusion_tag("fds_donation/stats/donation_chart.html", takes_context=True)
def donations_by_month(context):
    queryset = context["cl"].queryset
    donations = list(
        queryset.order_by()
        .filter(received_timestamp__isnull=False)
        .annotate(month=TruncMonth("timestamp"))
        .values("month", "recurring")
        .annotate(amount_by_month=Sum("amount"))
        .order_by("month", "recurring")
    )
    by_month = {(x["month"].isoformat(), x["recurring"]): x for x in donations}
    prev_year = relativedelta(years=1)
    # import ipdb ; ipdb.set_trace()
    for month_data in donations:
        key = ((month_data["month"] - prev_year).isoformat(), month_data["recurring"])
        if key in by_month:
            month_data["previous_year"] = by_month[key]["amount_by_month"]
        else:
            month_data["previous_year"] = None

    return {"chart_data": donations}
