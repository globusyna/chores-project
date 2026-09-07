from django.conf import settings
from django.db import models

from .exceptions import LedgerError


class PointTransaction(models.Model):
    """An immutable, append-only ledger entry (tasks.md #10).

    Never write these directly -- go through
    `ledger.services.record_transaction`, which also keeps
    `Profile.points_balance` in step inside one atomic block.
    """

    class Reason(models.TextChoices):
        BOUNTY_AWARD = "BOUNTY_AWARD", "Bounty award"
        PERK_DEBIT = "PERK_DEBIT", "Perk debit"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="point_transactions",
    )
    amount = models.IntegerField(help_text="Signed, non-zero.")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    related_bounty = models.ForeignKey(
        "chores.Bounty",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="point_transactions",
    )
    related_purchase = models.ForeignKey(
        "store.Purchase",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="point_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.user}: {self.amount:+d} ({self.get_reason_display()})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise LedgerError(
                "PointTransaction rows are append-only and cannot be modified."
            )
        super().save(*args, **kwargs)
