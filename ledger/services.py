from django.db import transaction
from django.db.models import F

from accounts.models import Profile

from .exceptions import LedgerError
from .models import PointTransaction


def record_transaction(
    user, amount, reason, *, related_bounty=None, related_purchase=None
):
    """Append one `PointTransaction` and move `Profile.points_balance` by the
    same signed amount, atomically. The only supported way to change a
    balance (tasks.md #10).

    Returns the created `PointTransaction`. Raises `LedgerError` if
    ``amount`` is zero.
    """
    if amount == 0:
        raise LedgerError("A point transaction amount must be non-zero.")

    with transaction.atomic():
        txn = PointTransaction.objects.create(
            user=user,
            amount=amount,
            reason=reason,
            related_bounty=related_bounty,
            related_purchase=related_purchase,
        )
        Profile.objects.filter(user=user).update(
            points_balance=F("points_balance") + amount
        )
    return txn
