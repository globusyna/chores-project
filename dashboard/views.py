from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, IntegerField, When
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from accounts.models import Profile
from accounts.permissions import child_required, parent_required
from chores.exceptions import InvalidTransition
from chores.models import Bounty
from ledger.models import PointTransaction
from ledger.services import record_transaction
from store.exceptions import InvalidTransition as PurchaseInvalidTransition
from store.models import Perk, Purchase

from .forms import BountyCreateForm


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
    # Lazy expiry revert so the board is correct between cron sweeps (#17).
    Bounty.objects.release_expired()
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


def _fragment_with_balance(request, template, context, status=200):
    """Row fragment + the out-of-band points-balance partial, so a
    point-changing action updates the header with no full-page reload
    (tasks.md #20). ``points_balance`` comes from the context processor.
    """
    html = render_to_string(template, context, request=request)
    html += render_to_string(
        "dashboard/_balance.html", {"oob": True}, request=request
    )
    return HttpResponse(html, status=status)


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
        Bounty.objects.filter(pk=bounty.pk).release_expired()
        bounty.refresh_from_db()
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


def _render_review_row(request, bounty, status=200):
    return render(
        request, "dashboard/_review_row.html", {"bounty": bounty}, status=status
    )


@parent_required
def review_queue(request):
    """Parent's queue of chores awaiting review (#14)."""
    bounties = (
        Bounty.objects.filter(status=Bounty.Status.PENDING_REVIEW)
        .select_related("claimed_by")
        .order_by("submitted_at", "id")
    )
    return render(request, "dashboard/review_queue.html", {"bounties": bounties})


@parent_required
@require_POST
def approve_bounty(request, pk):
    """Approve a submitted chore and award its points to the claimant (#14).

    The state flip and the point award happen in one atomic block; the
    ``approve()`` state check inside it means a double submit awards once.
    """
    get_object_or_404(Bounty, pk=pk)
    try:
        with transaction.atomic():
            bounty = Bounty.objects.select_for_update().get(pk=pk)
            recipient = bounty.claimed_by
            award = bounty.point_value
            bounty.approve(request.user)
            record_transaction(
                recipient,
                award,
                PointTransaction.Reason.BOUNTY_AWARD,
                related_bounty=bounty,
            )
    except InvalidTransition:
        return _render_review_row(request, bounty, status=409)
    # approve moves points -> refresh the header balance out of band (#20)
    return _fragment_with_balance(
        request, "dashboard/_review_row.html", {"bounty": bounty}
    )


@parent_required
@require_POST
def reject_bounty(request, pk):
    """Send a submitted chore back to the claimant as a do-over (#14).

    Back to CLAIMED with the claim fields and timer untouched; no ledger
    row.
    """
    get_object_or_404(Bounty, pk=pk)
    notes = request.POST.get("notes", "")
    try:
        with transaction.atomic():
            bounty = Bounty.objects.select_for_update().get(pk=pk)
            bounty.reject(request.user, notes=notes)
    except InvalidTransition:
        return _render_review_row(request, bounty, status=409)
    return _render_review_row(request, bounty)


@parent_required
def create_bounty(request):
    """Parent posts a one-off OPEN bounty, then lands back on the board (#15)."""
    if request.method == "POST":
        form = BountyCreateForm(request.POST)
        if form.is_valid():
            bounty = form.save(commit=False)
            bounty.status = Bounty.Status.OPEN
            bounty.created_by = request.user
            bounty.source_template = None
            bounty.save()
            return redirect("dashboard:board")
    else:
        form = BountyCreateForm()
    return render(request, "dashboard/bounty_form.html", {"form": form})


@login_required
def store(request):
    """Browse active perks alongside the viewer's point balance (#18)."""
    return render(
        request,
        "dashboard/store.html",
        {
            "perks": Perk.objects.filter(active=True),
            "balance": request.user.profile.points_balance,
        },
    )


def _render_perk_row(request, perk, *, message="", status=200):
    # Includes the OOB balance partial so the header stays current (#20).
    return _fragment_with_balance(
        request,
        "dashboard/_perk_row.html",
        {
            "perk": perk,
            "message": message,
            "balance": request.user.profile.points_balance,
        },
        status=status,
    )


@login_required
@require_POST
def buy_perk(request, pk):
    """Spend points on a perk, creating a LOCKED purchase (#18).

    No ledger write here -- ``points_balance`` is only debited at
    fulfilment (#19). The balance check and the insert happen under
    ``select_for_update`` on the profile so two racing buys can't both
    pass a balance that only covers one.
    """
    perk = get_object_or_404(Perk, pk=pk, active=True)

    with transaction.atomic():
        profile = Profile.objects.select_for_update().get(user=request.user)
        if profile.points_balance < perk.point_cost:
            return _render_perk_row(
                request,
                perk,
                message=(
                    f"Not enough points — {perk.title} costs {perk.point_cost}, "
                    f"you have {profile.points_balance}."
                ),
            )
        Purchase.objects.create(
            user=request.user, perk=perk, status=Purchase.Status.LOCKED
        )

    return _render_perk_row(
        request, perk, message="Purchased — waiting for a parent to hand it over."
    )


def _render_purchase_row(request, purchase, status=200):
    return render(
        request,
        "dashboard/_purchase_row.html",
        {"purchase": purchase},
        status=status,
    )


@parent_required
def fulfilment_queue(request):
    """Parent's queue of LOCKED purchases awaiting hand-over (#19)."""
    purchases = (
        Purchase.objects.filter(status=Purchase.Status.LOCKED)
        .select_related("perk", "user")
        .order_by("purchased_at", "id")
    )
    return render(
        request, "dashboard/fulfilment_queue.html", {"purchases": purchases}
    )


@parent_required
@require_POST
def fulfill_purchase(request, pk):
    """Mark a purchased perk delivered and finalise the point spend (#19).

    The state flip and the debit happen in one atomic block; the
    ``fulfill()`` state check inside it means a double submit debits once.
    The balance may go negative -- the reward is already handed over
    (open decision).
    """
    get_object_or_404(Purchase, pk=pk)
    try:
        with transaction.atomic():
            purchase = Purchase.objects.select_for_update().get(pk=pk)
            purchase.fulfill(request.user)
            record_transaction(
                purchase.user,
                -purchase.perk.point_cost,
                PointTransaction.Reason.PERK_DEBIT,
                related_purchase=purchase,
            )
    except PurchaseInvalidTransition:
        return _render_purchase_row(request, purchase, status=409)
    # fulfil moves points -> refresh the header balance out of band (#20)
    return _fragment_with_balance(
        request, "dashboard/_purchase_row.html", {"purchase": purchase}
    )
