from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from .exceptions import InvalidTransition

# Shared with the claim endpoint (#12) and the expiry sweep (#17).
# Do not inline "2 hours" anywhere else.
CLAIM_WINDOW = timedelta(hours=2)


class ChoreTemplate(models.Model):
    """A recurring chore definition used to repopulate the board (tasks.md #6).

    Spawning `Bounty` rows from templates is #16; this model is admin-only.
    """

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    default_point_value = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class BountyQuerySet(models.QuerySet):
    def release_expired(self):
        """Return every expired-but-still-CLAIMED bounty in this queryset to
        OPEN, clearing the claim fields (tasks.md #17). No rejection, no
        penalty (architecture.md §8). ``claim_expires_at == now`` counts as
        expired. Returns the number of rows reverted.

        The single shared revert path -- used by both the
        ``sweep_expired_claims`` command and the board view.
        """
        now = timezone.now()
        with transaction.atomic():
            return self.filter(
                status=Bounty.Status.CLAIMED,
                claim_expires_at__isnull=False,
                claim_expires_at__lte=now,
            ).update(
                status=Bounty.Status.OPEN,
                claimed_by=None,
                claimed_at=None,
                claim_expires_at=None,
            )


class Bounty(models.Model):
    """One chore instance on the board and its workflow state (tasks.md #7).

    The transition methods (`claim`, `submit`, `approve`, `reject`) each
    enforce their source state and persist their own change -- callers do
    not need a separate `save()`. An invalid transition raises
    `InvalidTransition` and mutates nothing.
    """

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLAIMED = "CLAIMED", "Claimed"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending review"
        APPROVED = "APPROVED", "Approved"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    point_value = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )

    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="claimed_bounties",
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    claim_expires_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_bounties",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    source_template = models.ForeignKey(
        "chores.ChoreTemplate",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bounties",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_bounties",
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    objects = BountyQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "bounties"

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_claim_expired(self):
        return (
            self.status == self.Status.CLAIMED
            and self.claim_expires_at is not None
            and self.claim_expires_at <= timezone.now()
        )

    def claim(self, user):
        """OPEN -> CLAIMED. Sets claimant + a fresh CLAIM_WINDOW timer."""
        if self.status != self.Status.OPEN:
            raise InvalidTransition(
                f"Cannot claim a bounty that is {self.get_status_display()}."
            )
        now = timezone.now()
        self.claimed_by = user
        self.claimed_at = now
        self.claim_expires_at = now + CLAIM_WINDOW
        self.status = self.Status.CLAIMED
        self.save(
            update_fields=[
                "claimed_by",
                "claimed_at",
                "claim_expires_at",
                "status",
            ]
        )

    def submit(self, user):
        """CLAIMED -> PENDING_REVIEW, by the claimant only."""
        if self.status != self.Status.CLAIMED:
            raise InvalidTransition(
                f"Cannot submit a bounty that is {self.get_status_display()}."
            )
        if user != self.claimed_by:
            raise InvalidTransition(
                "Only the user who claimed this bounty can submit it."
            )
        self.submitted_at = timezone.now()
        self.status = self.Status.PENDING_REVIEW
        self.save(update_fields=["submitted_at", "status"])

    def approve(self, reviewer):
        """PENDING_REVIEW -> APPROVED. Flips state only; the point award is
        #14 via #10's helper."""
        if self.status != self.Status.PENDING_REVIEW:
            raise InvalidTransition(
                f"Cannot approve a bounty that is {self.get_status_display()}."
            )
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.status = self.Status.APPROVED
        self.save(update_fields=["reviewed_by", "reviewed_at", "status"])

    def reject(self, reviewer, notes=""):
        """PENDING_REVIEW -> CLAIMED (a do-over). The claim fields and timer
        are left untouched -- no new window (architecture.md §5)."""
        if self.status != self.Status.PENDING_REVIEW:
            raise InvalidTransition(
                f"Cannot reject a bounty that is {self.get_status_display()}."
            )
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.status = self.Status.CLAIMED
        self.save(
            update_fields=["reviewed_by", "reviewed_at", "review_notes", "status"]
        )
