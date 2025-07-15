from django.utils import timezone

import pytest

from ..models import Newsletter, Segment
from ..utils import get_subscribers
from .factories import SubscriberFactory


@pytest.fixture
def newsletter():
    """Fixture to create a newsletter."""
    return Newsletter.objects.create(
        title="Test Newsletter",
        slug="test-newsletter",
        description="Test description",
    )


@pytest.fixture
def subscriber_factory():
    def factory(newsletter, tags=None, subscribed=True):
        sub = SubscriberFactory.create(
            newsletter=newsletter, subscribed=timezone.now() if subscribed else None
        )
        if tags:
            sub.tags.set(tags)
        return sub

    return factory


@pytest.fixture
def segment_factory():
    def factory(parent=None, tags=None, negate=False):
        if parent is None:
            segment = Segment.add_root(
                name="Test Root Segment [{}]".format(", ".join(tags if tags else [])),
                negate=negate,
            )
        else:
            segment = parent.add_child(
                name="Test Child Segment [{}]".format(", ".join(tags if tags else [])),
                negate=negate,
            )

        if tags:
            segment.tags.set(tags)
        return segment

    return factory


@pytest.mark.django_db
def test_get_subscribers_no_newsletter():
    """Test get_subscribers when no newsletter is provided."""
    result = get_subscribers(None)
    assert result.count() == 0


@pytest.mark.django_db
def test_get_subscribers_for_newsletter(newsletter, subscriber_factory):
    """Test get_subscribers when no segments are provided."""
    subscriber_factory(newsletter, subscribed=timezone.now())
    subscriber_factory(newsletter, subscribed=None)  # Unsubscribed

    result = get_subscribers(newsletter)
    assert result.count() == 1  # Only the subscribed subscriber is returned


@pytest.mark.django_db
def test_get_subscribers_with_segments(newsletter, subscriber_factory, segment_factory):
    """Test get_subscribers with segments filtering."""

    subscriber1 = subscriber_factory(newsletter, tags=["tag1"])
    subscriber2 = subscriber_factory(newsletter, tags=["tag1", "tag2"])
    subscriber3 = subscriber_factory(newsletter, tags=["tag2"])
    _subscriber4 = subscriber_factory(newsletter, tags=["tag3"])

    segment1 = segment_factory(tags=["tag1"])
    segment2 = segment_factory(tags=["tag1", "tag2"])
    segment3 = segment_factory(tags=["tag2"])

    result = get_subscribers(newsletter, segments=[segment1])
    assert {subscriber1, subscriber2} == set(result)

    result = get_subscribers(newsletter, segments=[segment2])
    assert {subscriber2} == set(result)

    result = get_subscribers(newsletter, segments=[segment3])
    assert {subscriber2, subscriber3} == set(result)

    result = get_subscribers(newsletter, segments=[segment1, segment2])
    assert {subscriber1, subscriber2} == set(result)

    result = get_subscribers(newsletter, segments=[segment1, segment3])
    assert {subscriber1, subscriber2, subscriber3} == set(result)


@pytest.mark.django_db
def test_segment_filter_subscribers_with_children(
    newsletter, subscriber_factory, segment_factory
):
    """Test Segment parent with child segments."""

    _subscriber1 = subscriber_factory(newsletter, tags={"tag1"})
    subscriber2 = subscriber_factory(newsletter, tags={"tag1", "tag2"})
    subscriber3 = subscriber_factory(newsletter, tags={"tag1", "tag3"})
    _subscriber4 = subscriber_factory(newsletter, tags={"tag4"})

    parent_segment = segment_factory()
    child_segment1 = segment_factory(tags=["tag2"], parent=parent_segment)
    child_segment2 = segment_factory(tags=["tag2", "tag_bad"], parent=parent_segment)
    child_segment3 = segment_factory(tags=["tag3"], parent=parent_segment)

    result = get_subscribers(newsletter, segments=[child_segment1])
    assert {subscriber2} == set(result)

    result = get_subscribers(newsletter, segments=[child_segment2])
    assert set() == set(result)

    result = get_subscribers(newsletter, segments=[child_segment3])
    assert {subscriber3} == set(result)

    result = get_subscribers(newsletter, segments=[parent_segment])
    assert set() == set(result)

    result = get_subscribers(newsletter, segments=[child_segment1, child_segment3])
    assert {subscriber2, subscriber3} == set(result)


@pytest.mark.django_db
def test_segment_filter_subscribers_with_parent_tag(
    newsletter, subscriber_factory, segment_factory
):
    """Test Segment parent with tag and with child segments."""

    _subscriber1 = subscriber_factory(newsletter, tags={"tag1"})
    subscriber2 = subscriber_factory(newsletter, tags={"tag1", "tag2"})
    subscriber3 = subscriber_factory(newsletter, tags={"tag3", "tag1"})
    _subscriber4 = subscriber_factory(newsletter, tags={"tag4"})

    parent_segment = segment_factory(tags=["tag1"])
    child_segment1 = segment_factory(tags=["tag2"], parent=parent_segment)
    child_segment2 = segment_factory(tags=["tag2", "tag_bad"], parent=parent_segment)
    child_segment3 = segment_factory(tags=["tag3"], parent=parent_segment)

    result = get_subscribers(newsletter, segments=[child_segment1])
    assert {subscriber2} == set(result)

    result = get_subscribers(newsletter, segments=[child_segment2])
    assert set() == set(result)

    result = get_subscribers(newsletter, segments=[child_segment3])
    assert {subscriber3} == set(result)

    result = get_subscribers(newsletter, segments=[parent_segment])
    assert set() == set(result)


@pytest.mark.django_db
def test_segment_filter_subscribers_with_parent_tag_intersection(
    newsletter, subscriber_factory, segment_factory
):
    """Test Segment parent with tag and with child segments."""

    _subscriber1 = subscriber_factory(newsletter, tags={"tag1"})
    _subscriber2 = subscriber_factory(newsletter, tags={"tag1", "tag2"})
    subscriber3 = subscriber_factory(newsletter, tags={"tag3", "tag1"})
    _subscriber4 = subscriber_factory(newsletter, tags={"tag4"})

    parent_segment = segment_factory(tags=["tag1"])
    child_segment = segment_factory(tags=["tag3"], parent=parent_segment)

    result = get_subscribers(newsletter, segments=[child_segment])
    assert {subscriber3} == set(result)

    result = get_subscribers(newsletter, segments=[parent_segment])
    assert {subscriber3} == set(result)


@pytest.mark.django_db
def test_segment_negated_tags(newsletter, subscriber_factory, segment_factory):
    """Test Segment parent with tag and with child segments."""

    subscriber1 = subscriber_factory(newsletter, tags={"tag1"})
    subscriber2 = subscriber_factory(newsletter, tags={"tag1", "tag2"})
    subscriber3 = subscriber_factory(newsletter, tags={"tag3"})
    subscriber4 = subscriber_factory(newsletter, tags={"tag4"})

    parent_segment = segment_factory(tags=["tag1"], negate=True)
    child_segment1 = segment_factory(tags=["tag2"], parent=parent_segment, negate=True)
    child_segment2 = segment_factory(
        tags=["tag2", "tag_bad"], parent=parent_segment, negate=True
    )
    child_segment3 = segment_factory(tags=["tag3"], parent=parent_segment, negate=True)

    result = get_subscribers(newsletter, segments=[child_segment1])
    assert {subscriber1, subscriber3, subscriber4} == set(result)

    result = get_subscribers(newsletter, segments=[child_segment2])
    assert {subscriber1, subscriber3, subscriber4} == set(result)

    result = get_subscribers(newsletter, segments=[child_segment3])
    assert {subscriber1, subscriber2, subscriber4} == set(result)

    result = get_subscribers(newsletter, segments=[parent_segment])
    assert {subscriber4} == set(result)
