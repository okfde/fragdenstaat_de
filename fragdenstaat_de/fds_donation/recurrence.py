from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from django.db.models import Count
from django.utils import timezone

from dateutil.relativedelta import relativedelta
from froide_payment.models import Subscription

from .models import Donation, Donor, Recurrence


@dataclass
class DonationStreak:
    donations: list[Donation]
    interval: int
    method: str
    canceled: Optional[datetime] = None


def find_donation_streaks(
    donations: list[Donation],
    current_date: datetime | None = None,
) -> list[DonationStreak]:
    """
    Analyze transactions to find recurrences or streaks based on amounts and intervals.

    Args:
        transactions: list of dictionaries with at least 'date' and 'amount' keys
                    ('date' can be string 'YYYY-MM-DD' or datetime object)
        current_date: The current date as a datetime object

    Returns:
        list of dictionaries containing streak information with:
        - 'first_transaction': The first transaction in the streak
        - 'last_transaction': The last transaction in the streak
        - 'count': Number of transactions in the streak
        - 'total_amount': Sum of all transaction amounts in the streak
        - 'avg_interval': Average interval between transactions (in days)
        - 'interval_type': Identified recurrence pattern (e.g., "weekly", "monthly")
        - 'days_since_last': Days since the last transaction in the streak
        - 'next_expected': Estimated date of next transaction in streak
    """
    if not donations:
        return []

    if current_date is None:
        current_date = timezone.now()

    all_streaks = []
    # Sort transactions by date
    sorted_transactions = sorted(donations, key=lambda x: x.received_timestamp)

    # Group transactions by amount (with tolerance)
    keyed_groups = defaultdict(list)

    def make_key(tx):
        return (tx.amount, tx.method)

    for tx in sorted_transactions:
        # Find a matching amount group or create a new one
        matched = False
        key = make_key(tx)
        for group_key in list(keyed_groups.keys()):
            if key == group_key:
                keyed_groups[group_key].append(tx)
                matched = True
                break

        if not matched:
            keyed_groups[key].append(tx)

    for _key, group_txs in keyed_groups.items():
        if len(group_txs) < 2:
            continue  # Skip single transactions

        # Sort transactions in this amount group by date
        group_txs = sorted(group_txs, key=lambda x: x.received_timestamp)

        # Try to identify recurring patterns
        potential_patterns = identify_recurring_patterns(group_txs)

        for pattern_type, pattern_streaks in potential_patterns.items():
            for streak in pattern_streaks:
                cancel_date = get_cancel_date(streak, pattern_type, current_date)
                example = streak[0]
                all_streaks.append(
                    DonationStreak(
                        donations=streak,
                        interval=pattern_type,
                        method=example.method,
                        canceled=cancel_date,
                    )
                )

    # Sort streaks by recency (days since last transaction)
    return all_streaks


def get_cancel_date(
    donations: list[Donation], interval: int, now: datetime
) -> Optional[datetime]:
    """
    Check if a streak is canceled based on the last donation's cancel date.
    """

    last_date = donations[-1].received_timestamp
    if last_date is None:
        return None

    next_expected = last_date + relativedelta(months=interval)
    if next_expected < now:
        return last_date
    return None


def identify_recurring_patterns(
    transactions: list[Donation],
) -> dict[int, list[list[Donation]]]:
    """
    Identify recurring patterns in transactions of the same amount.
    Uses a greedy approach to find the best pattern match and avoid duplicates.

    Returns a dictionary mapping pattern types to lists of transaction streaks.
    """
    if len(transactions) < 2:
        return {}

    # Define acceptable ranges for different recurring patterns (in days)
    # Order matters - we'll try patterns from most frequent to least frequent
    pattern_ranges = [
        (1, (25, 35)),  # Around 30 days
        (3, (80, 100)),  # Around 90 days
        (6, (170, 190)),  # Around 180 days
        (12, (350, 380)),  # Around 365 days
    ]

    # Find all possible streaks for each pattern type
    all_possible_streaks = {}

    for pattern_type, (min_days, max_days) in pattern_ranges:
        streaks = find_streaks_for_pattern(transactions, min_days, max_days)
        if streaks:
            all_possible_streaks[pattern_type] = streaks

    # Now select the best non-overlapping streaks
    selected_patterns = {}
    used_transactions = set()

    # Process patterns in order of specificity (shortest intervals first)
    for pattern_type, streaks in all_possible_streaks.items():
        selected_patterns[pattern_type] = []

        # Sort streaks by length (longer streaks are preferred)
        streaks = sorted(streaks, key=lambda s: len(s), reverse=True)

        for streak in streaks:
            # Check if any transaction in this streak is already used
            streak_set = set(streak)
            if not streak_set.intersection(used_transactions):
                # This streak doesn't overlap with already selected streaks
                selected_patterns[pattern_type].append(streak)
                used_transactions.update(streak_set)

    return selected_patterns


def find_streaks_for_pattern(
    transactions: list[Donation], min_days: int, max_days: int
) -> set[list[Donation]]:
    """Find all possible streaks that match a specific pattern interval."""
    streaks = set()

    # Try starting from each transaction
    for start_idx in range(len(transactions)):
        current_streak = [transactions[start_idx]]

        # Look for subsequent transactions that fit the pattern
        for next_idx in range(start_idx + 1, len(transactions)):
            days_diff = (
                transactions[next_idx].received_timestamp
                - current_streak[-1].received_timestamp
            ).days

            # If this transaction fits the pattern interval
            if min_days <= days_diff <= max_days:
                current_streak.append(transactions[next_idx])
            # If the gap is too large, we can't continue this streak
            elif days_diff > max_days:
                break

        # Only keep streaks with at least 2 transactions
        if len(current_streak) >= 2:
            streaks.add(tuple(current_streak))

    return streaks


def process_recurrence_on_donor(donor: Donor):
    donations = Donation.objects.filter(
        donor=donor, received_timestamp__isnull=False, order__subscription__isnull=False
    )
    if donations:
        process_subscription_donations(donor, donations)

    donations = Donation.objects.filter(
        donor=donor,
        received_timestamp__isnull=False,
        order__subscription__isnull=True,
    )
    if donations:
        process_donations(donor, donations)


def process_subscription_donations(donor: Donor, donations):
    subscriptions = defaultdict(list)
    for donation in donations:
        subscriptions[donation.order.subscription].append(donation)

    for subscription, subscription_donations in subscriptions.items():
        recurrence = create_recurrence_for_subscription(donor, subscription)
        Donation.objects.filter(
            id__in=[donation.id for donation in subscription_donations]
        ).update(recurrence=recurrence)


def process_donations(donor: Donor, donations):
    streaks = find_donation_streaks(donations)

    streak_donations = set()

    for streak in streaks:
        existing_recurrences = set()
        missing_recurrences = set()
        streak_donations |= set(streak.donations)
        for donation in streak.donations:
            if donation.recurrence:
                existing_recurrences.add(donation.recurrence)
            else:
                missing_recurrences.add(donation)
        # Determine the correct recurrence for the streak
        if not existing_recurrences:
            recurrence = create_recurrence_for_streak(streak)
        elif len(existing_recurrences) == 1:
            recurrence = existing_recurrences.pop()
        else:
            # Multiple recurrences found, we need to create a new one
            recurrence, other_recurrences = combine_existing_recurrences(
                existing_recurrences
            )
            Donation.objects.filter(
                id__in=[donation.id for donation in streak.donations]
            ).filter(recurrence__in=other_recurrences).update(recurrence=recurrence)

        if existing_recurrences:
            update_recurrence(recurrence, streak)

        if missing_recurrences:
            Donation.objects.filter(
                id__in=[donation.id for donation in streak.donations]
            ).update(recurrence=recurrence)

    # Remove recurrence from selected donations not detected as streaks
    donations.filter(recurrence__isnull=False).exclude(
        id__in=[donation.id for donation in streak_donations]
    ).update(recurrence=None)
    # Remove recurrences that have no donations associated
    Recurrence.objects.filter(donor=donor).annotate(
        donation_count=Count("donations", distinct=True)
    ).filter(donation_count=0).delete()


def update_recurrence(recurrence: Recurrence, streak: DonationStreak):
    changed = []
    if recurrence.start_date != streak.donations[0].received_timestamp:
        recurrence.start_date = streak.donations[0].received_timestamp
        changed.append("start_date")
    if recurrence.amount != streak.donations[-1].amount:
        recurrence.amount = streak.donations[-1].amount
        changed.append("amount")
    if recurrence.interval != streak.interval:
        recurrence.interval = streak.interval
        changed.append("interval")
    if recurrence.method != streak.method:
        recurrence.method = streak.method
        changed.append("method")
    if recurrence.cancel_date != streak.canceled:
        recurrence.cancel_date = streak.canceled
        changed.append("cancel_date")
    if changed:
        recurrence.save(update_fields=changed)


def create_recurrence_for_subscription(donor: Donor, subscription: Subscription):
    recurrence, _updated = Recurrence.objects.update_or_create(
        subscription=subscription,
        defaults={
            "donor": donor,
            "start_date": subscription.created,
            "interval": subscription.plan.interval,
            "amount": subscription.plan.amount,
            "method": subscription.plan.provider,
            "cancel_date": subscription.canceled,
        },
    )
    return recurrence


def create_recurrence_for_streak(streak: DonationStreak):
    """
    Create a recurrence for the given donation streak.
    This function should be implemented to handle the creation logic.
    """
    first_donation = streak.donations[0]
    last_donation = streak.donations[-1]
    Recurrence.objects.create(
        donor=first_donation.donor,
        start_date=first_donation.received_timestamp,
        interval=streak.interval,
        amount=last_donation.amount,
        cancel_date=streak.canceled,
    )


def combine_existing_recurrences(
    duplicate_recurrences: set[Recurrence],
) -> tuple[Recurrence, list[Recurrence]]:
    """
    Combine multiple existing recurrences into one.
    """

    recurrences = list(duplicate_recurrences)
    first_recurrence = recurrences[0]
    other_recurrences = recurrences[1:]

    return first_recurrence, other_recurrences
