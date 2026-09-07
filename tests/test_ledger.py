"""Point ledger model & record_transaction helper (tasks.md #10)."""

import pytest
from django.db.models import Sum

from chores.models import Bounty
from ledger.exceptions import LedgerError
from ledger.models import PointTransaction
from ledger.services import record_transaction
from store.models import Perk, Purchase

pytestmark = pytest.mark.django_db

Reason = PointTransaction.Reason


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="kid", password="pw")


def test_new_profile_starts_at_zero(user):
    assert user.profile.points_balance == 0


def test_record_transaction_creates_row_and_moves_balance(user):
    txn = record_transaction(user, 10, Reason.BOUNTY_AWARD)

    assert isinstance(txn, PointTransaction)
    assert txn.pk is not None
    user.profile.refresh_from_db()
    assert user.profile.points_balance == 10


def test_debit_moves_balance_negative_direction(user):
    record_transaction(user, 30, Reason.BOUNTY_AWARD)
    record_transaction(user, -12, Reason.PERK_DEBIT)

    user.profile.refresh_from_db()
    assert user.profile.points_balance == 18


def test_zero_amount_is_rejected_and_writes_nothing(user):
    with pytest.raises(LedgerError):
        record_transaction(user, 0, Reason.ADJUSTMENT)

    assert PointTransaction.objects.count() == 0
    user.profile.refresh_from_db()
    assert user.profile.points_balance == 0


def test_point_transaction_is_append_only(user):
    txn = record_transaction(user, 5, Reason.ADJUSTMENT)

    txn.amount = 999
    with pytest.raises(LedgerError):
        txn.save()

    txn.refresh_from_db()
    assert txn.amount == 5


def test_related_objects_are_linked(user):
    perk = Perk.objects.create(title="Ice cream", point_cost=4)
    purchase = Purchase.objects.create(perk=perk, user=user)
    bounty = Bounty.objects.create(title="Dishes", point_value=6)

    award = record_transaction(
        user, 6, Reason.BOUNTY_AWARD, related_bounty=bounty
    )
    debit = record_transaction(
        user, -4, Reason.PERK_DEBIT, related_purchase=purchase
    )

    assert award.related_bounty == bounty
    assert debit.related_purchase == purchase


def test_balance_always_equals_ledger_sum(user, django_user_model):
    other = django_user_model.objects.create_user(username="kid2", password="pw")

    for amount, reason in [
        (10, Reason.BOUNTY_AWARD),
        (25, Reason.BOUNTY_AWARD),
        (-8, Reason.PERK_DEBIT),
        (3, Reason.ADJUSTMENT),
        (-15, Reason.PERK_DEBIT),
        (7, Reason.BOUNTY_AWARD),
    ]:
        record_transaction(user, amount, reason)

    record_transaction(other, 100, Reason.ADJUSTMENT)  # must not leak across

    user.profile.refresh_from_db()
    ledger_sum = PointTransaction.objects.filter(user=user).aggregate(
        total=Sum("amount")
    )["total"]
    assert user.profile.points_balance == ledger_sum == 22

    other.profile.refresh_from_db()
    assert other.profile.points_balance == 100
