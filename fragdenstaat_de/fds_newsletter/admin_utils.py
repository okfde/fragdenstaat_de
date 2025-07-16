from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from froide.helper.admin_utils import (
    make_batch_tag_action,
)

from .admin import SUBSCRIBER_TAG_AUTOCOMPLETE_URL
from .models import Subscriber, SubscriberTag, TaggedSubscriber


def make_subscriber_tagger(
    email_queryset_function,
    convert_queryset_function=None,
    action_name="tag_subscribers",
    short_description=None,
):
    if short_description is None:
        short_description = _("Tag newsletter subscribers")

    def convert_queryset(queryset):
        """
        Convert the queryset to a list of subscriber IDs.
        """
        emails = email_queryset_function(queryset)
        return Subscriber.objects.filter(
            Q(email__in=emails) | Q(user__email__in=emails)
        )

    if convert_queryset_function:
        convert_queryset = convert_queryset_function

    return make_batch_tag_action(
        action_name=action_name,
        autocomplete_url=SUBSCRIBER_TAG_AUTOCOMPLETE_URL,
        short_description=short_description,
        convert_queryset=convert_queryset,
        apply_tags=apply_tags_to_subscribers,
    )


def apply_tags_to_subscribers(tags: list[str], queryset, field="tags"):
    """
    Apply tags to a queryset of subscribers.
    """
    if not tags:
        return

    tags = [SubscriberTag.objects.get_or_create(name=tag)[0] for tag in tags]

    for tag in tags:
        TaggedSubscriber.objects.bulk_create(
            [
                TaggedSubscriber(content_object_id=subscriber_id, tag=tag)
                for subscriber_id in queryset.values_list("id", flat=True)
            ],
            ignore_conflicts=True,
        )
