from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Count, Sum

import requests

from .models import Newsletter, Subscriber


def get_analytics(start_date, end_date, newsletter=None):
    if newsletter is None:
        newsletter = Newsletter.objects.get(slug=settings.DEFAULT_NEWSLETTER)

    data = {}
    subscribers = Subscriber.objects.filter(newsletter=newsletter).filter(
        subscribed__date__gte=start_date, subscribed__date__lt=end_date
    )
    data["new_subscriber_count"] = subscribers.count()
    subscriber_references = (
        subscribers.values("reference")
        .annotate(count=Count("reference"))
        .order_by("-count")
    )
    for subscriber_reference in subscriber_references:
        data[
            "new_subscriber_count_" + subscriber_reference["reference"]
        ] = subscriber_reference["count"]

    unsubscribers = Subscriber.objects.filter(newsletter=newsletter).filter(
        unsubscribed__date__gte=start_date, unsubscribed__date__lt=end_date
    )
    data["unsubscriber_count"] = unsubscribers.count()
    unsubscriber_references = (
        unsubscribers.values("reference")
        .annotate(count=Count("reference"))
        .order_by("-count")
    )
    for unsubscriber_reference in unsubscriber_references:
        data[
            "unsubscriber_count_" + unsubscriber_reference["reference"]
        ] = unsubscriber_reference["count"]

    data.update(get_donation_data(start_date, end_date, "newsletter"))
    data.update(get_matomo_data(start_date, end_date, "newsletter"))
    return data


def get_donation_data(start_date, end_date, reference_name):
    from fragdenstaat_de.fds_donation.models import Donation

    data = Donation.objects.filter(
        timestamp__date__gte=start_date,
        timestamp__date__lt=end_date,
        completed=True,
        reference=reference_name,
    ).aggregate(
        donations_total=Sum("amount"),
        donations_count=Count("id"),
    )
    return {
        "donations_reference_newsletter_amount": float(data["donations_total"]),
        "donations_reference_newsletter_count": data["donations_count"],
    }


def get_matomo_data(start_date, end_date, referrer_name):
    if not settings.MATOMO_API_URL:
        return {}
    # end date is inclusive in API
    end_date = end_date - timedelta(days=1)
    query_params = {
        "module": "API",
        "method": "Referrers.getCampaigns",
        "period": "range",
        "date": start_date.strftime("%Y-%m-%d") + "," + end_date.strftime("%Y-%m-%d"),
        "segment": "referrerName=={}".format(referrer_name),
    }
    url = settings.MATOMO_API_URL + "&" + urlencode(query_params)
    data = requests.get(url).json()
    if not len(data):
        return {}
    base_data = data[0]
    goal_key = "idgoal={}".format(settings.MATOMO_GOAL_ID)
    goal_conversions = (
        base_data.get("goals", {}).get(goal_key, {}).get("nb_conversions", 0)
    )

    return {
        "visits": base_data["nb_visits"],
        "goal_conversions": goal_conversions,
        "goal_conversion_percentage": (
            goal_conversions / base_data["nb_visits"]
            if base_data["nb_visits"] > 0
            else 0
        )
        * 100,
    }

    # query_params.update(
    #     {
    #         "method": "Referrers.getKeywordsFromCampaignId",
    #         "idSubtable": base_data["idsubdatatable"],
    #     }
    # )
    # url = settings.MATOMO_API_URL + "&" + urlencode(query_params)
    # keyword_data = requests.get(url).json()
