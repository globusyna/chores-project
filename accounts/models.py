from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Per-user role record (tasks.md #4).

    Every ``User`` gets exactly one ``Profile`` via a ``post_save`` signal
    (see ``accounts/signals.py``). New profiles start as ``CHILD``; a parent
    is promoted by hand in the Django admin.
    """

    class Role(models.TextChoices):
        PARENT = "PARENT", "Parent"
        CHILD = "CHILD", "Child"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=6,
        choices=Role.choices,
        default=Role.CHILD,
    )
    # Denormalised cache of the point ledger sum (tasks.md #10). Only
    # ledger.services.record_transaction may write this.
    points_balance = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user} ({self.get_role_display()})"
