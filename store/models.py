from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .exceptions import InvalidTransition


class Perk(models.Model):
    """An item a user can redeem points for (tasks.md #8).

    The `Purchase` model and its workflow are #9; this model is admin-only.
    """

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    point_cost = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Purchase(models.Model):
    """One perk purchase and its fulfilment workflow (tasks.md #9).

    `fulfill()` flips state only -- the debit `PointTransaction` and balance
    update are #19 via #10's helper. This model does not touch points.
    """

    class Status(models.TextChoices):
        LOCKED = "LOCKED", "Locked"
        FULFILLED = "FULFILLED", "Fulfilled"

    perk = models.ForeignKey(
        Perk, on_delete=models.PROTECT, related_name="purchases"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.LOCKED
    )
    purchased_at = models.DateTimeField(default=timezone.now)
    fulfilled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fulfilled_purchases",
    )
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.user} → {self.perk} ({self.get_status_display()})"

    def fulfill(self, parent):
        """LOCKED -> FULFILLED. Persists itself; no caller `save()` needed."""
        if self.status != self.Status.LOCKED:
            raise InvalidTransition(
                f"Cannot fulfil a purchase that is {self.get_status_display()}."
            )
        self.fulfilled_by = parent
        self.fulfilled_at = timezone.now()
        self.status = self.Status.FULFILLED
        self.save(update_fields=["fulfilled_by", "fulfilled_at", "status"])
