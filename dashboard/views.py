from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, IntegerField, When
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from accounts.permissions import child_required
from chores.exceptions import InvalidTransition
from chores.models import Bounty


def home(request):
    """Landing page for the bounty board.

    Intentionally minimal for now (project scaffolding) — later tasks
    replace this with the read-only bounty board (see _docs/tasks.md #11).
    """
    return render(request, "dashboard/home.html")


# Board display order: OPEN first, then CLAIMED, then PENDING_REVIEW;
# within a status, higher point value first (tasks.md #11).
_STATUS_RANK = Case(
    When(status=Bounty.Status.OPEN, then=0),
    When(status=Bounty.Status.CLAIMED, then=1),
    When(status=Bounty.Status.PENDING_REVIEW, then=2),
    default=3,
    output_field=IntegerField(),
)


@login_required
def board(request):
    """Read-only list of every bounty that isn't approved yet (tasks.md #11).

    Display only — no claim/submit/review actions (those are #12–#14, which
    re-render ``dashboard/_bounty_row.html``).
    """
    bounties = (
        Bounty.objects.exclude(status=Bounty.Status.APPROVED)
        .select_related("claimed_by")
        .annotate(status_rank=_STATUS_RANK)
        .order_by("status_rank", "-point_value", "id")
    )
    return render(request, "dashboard/board.html", {"bounties": bounties})


def _render_row(request, bounty, status=200):
    return render(
        request, "dashboard/_bounty_row.html", {"bounty": bounty}, status=status
    )


@child_required
@require_POST
def claim_bounty(request, pk):
    """Child claims an OPEN bounty; returns the updated row fragment (#12).

    403 if the requester is not a child, 409 if the bounty is not OPEN,
    404 if it is missing, 405 on GET. One winner under concurrency via
    ``select_for_update`` inside the transaction.
    """
    get_object_or_404(Bounty, pk=pk)
    try:
        with transaction.atomic():
            bounty = Bounty.objects.select_for_update().get(pk=pk)
            bounty.claim(request.user)
    except InvalidTransition:
        return _render_row(request, bounty, status=409)
    return _render_row(request, bounty)


def _revert_expired_claim(bounty):
    """Return an expired-but-unswept claim to the board.

    TODO(#17): replace with the shared ``Bounty.objects.release_expired()``
    manager method once the claim-expiry sweep lands.
    """
    bounty.status = Bounty.Status.OPEN
    bounty.claimed_by = None
    bounty.claimed_at = None
    bounty.claim_expires_at = None
    bounty.save(
        update_fields=["status", "claimed_by", "claimed_at", "claim_expires_at"]
    )


@login_required
@require_POST
def submit_bounty(request, pk):
    """Claimant marks their chore done and ready for review (#13).

    403 if the bounty is not claimed by this user, 409 if it is not in
    CLAIMED, 404 if missing, 405 on GET. If the claim window has already
    passed, the row is reverted to OPEN inline and the submit is rejected.
    """
    bounty = get_object_or_404(Bounty, pk=pk)

    if bounty.is_claim_expired:
        _revert_expired_claim(bounty)
        return _render_row(request, bounty, status=409)

    if (
        bounty.status == Bounty.Status.CLAIMED
        and bounty.claimed_by_id != request.user.id
    ):
        return _render_row(request, bounty, status=403)

    try:
        with transaction.atomic():
            bounty = Bounty.objects.select_for_update().get(pk=pk)
            bounty.submit(request.user)
    except InvalidTransition:
        return _render_row(request, bounty, status=409)
    return _render_row(request, bounty)
