"""Bounty model & state machine (tasks.md #7)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from chores.exceptions import InvalidTransition
from chores.models import CLAIM_WINDOW, Bounty

pytestmark = pytest.mark.django_db

Status = Bounty.Status


@pytest.fixture
def claimant(django_user_model):
    return django_user_model.objects.create_user(username="kid", password="pw")


@pytest.fixture
def other(django_user_model):
    return django_user_model.objects.create_user(username="kid2", password="pw")


@pytest.fixture
def reviewer(django_user_model):
    return django_user_model.objects.create_user(username="mum", password="pw")


@pytest.fixture
def bounty():
    return Bounty.objects.create(title="Mow the lawn", point_value=10)


def _snapshot(b):
    b.refresh_from_db()
    return {f.name: getattr(b, f.attname) for f in Bounty._meta.fields}


# --- claim -----------------------------------------------------------------

def test_claim_from_open_sets_exactly_the_claim_fields(bounty, claimant):
    before = timezone.now()
    bounty.claim(claimant)
    after = timezone.now()

    bounty.refresh_from_db()
    assert bounty.status == Status.CLAIMED
    assert bounty.claimed_by == claimant
    assert before <= bounty.claimed_at <= after
    assert bounty.claim_expires_at == bounty.claimed_at + CLAIM_WINDOW
    assert CLAIM_WINDOW == timedelta(hours=2)
    assert bounty.submitted_at is None
    assert bounty.reviewed_by_id is None


@pytest.mark.parametrize("bad_status", [Status.CLAIMED, Status.PENDING_REVIEW, Status.APPROVED])
def test_claim_from_non_open_raises_and_mutates_nothing(bounty, claimant, bad_status):
    Bounty.objects.filter(pk=bounty.pk).update(status=bad_status)
    bounty.refresh_from_db()
    snap = _snapshot(bounty)

    with pytest.raises(InvalidTransition):
        bounty.claim(claimant)

    assert _snapshot(bounty) == snap


# --- submit --------------------------------------------------------------

def test_submit_from_claimed_by_claimant(bounty, claimant):
    bounty.claim(claimant)
    before = timezone.now()
    bounty.submit(claimant)

    bounty.refresh_from_db()
    assert bounty.status == Status.PENDING_REVIEW
    assert bounty.submitted_at >= before
    # claim fields untouched
    assert bounty.claimed_by == claimant


def test_submit_by_non_claimant_raises_and_mutates_nothing(bounty, claimant, other):
    bounty.claim(claimant)
    snap = _snapshot(bounty)

    with pytest.raises(InvalidTransition):
        bounty.submit(other)

    assert _snapshot(bounty) == snap


def test_submit_on_open_raises(bounty, claimant):
    with pytest.raises(InvalidTransition):
        bounty.submit(claimant)
    assert _snapshot(bounty)["status"] == Status.OPEN


def test_submit_twice_second_raises(bounty, claimant):
    bounty.claim(claimant)
    bounty.submit(claimant)
    with pytest.raises(InvalidTransition):
        bounty.submit(claimant)


# --- approve -----------------------------------------------------------

def test_approve_from_pending_review(bounty, claimant, reviewer):
    bounty.claim(claimant)
    bounty.submit(claimant)
    before = timezone.now()
    bounty.approve(reviewer)

    bounty.refresh_from_db()
    assert bounty.status == Status.APPROVED
    assert bounty.reviewed_by == reviewer
    assert bounty.reviewed_at >= before


def test_approve_on_claimed_raises_and_mutates_nothing(bounty, claimant, reviewer):
    bounty.claim(claimant)
    snap = _snapshot(bounty)
    with pytest.raises(InvalidTransition):
        bounty.approve(reviewer)
    assert _snapshot(bounty) == snap


# --- reject ------------------------------------------------------------

def test_reject_from_pending_review_preserves_claim(bounty, claimant, reviewer):
    bounty.claim(claimant)
    claimed_by = bounty.claimed_by
    claimed_at = bounty.claimed_at
    claim_expires_at = bounty.claim_expires_at
    bounty.submit(claimant)

    bounty.reject(reviewer, notes="Missed a spot")

    bounty.refresh_from_db()
    assert bounty.status == Status.CLAIMED
    assert bounty.review_notes == "Missed a spot"
    assert bounty.reviewed_by == reviewer
    assert bounty.reviewed_at is not None
    assert bounty.claimed_by == claimed_by
    assert bounty.claimed_at == claimed_at
    assert bounty.claim_expires_at == claim_expires_at


def test_reject_defaults_notes_to_empty_string(bounty, claimant, reviewer):
    bounty.claim(claimant)
    bounty.submit(claimant)
    bounty.reject(reviewer)
    bounty.refresh_from_db()
    assert bounty.review_notes == ""


def test_reject_on_open_raises(bounty, reviewer):
    with pytest.raises(InvalidTransition):
        bounty.reject(reviewer)


# --- terminal state --------------------------------------------------

def test_no_transition_out_of_approved(bounty, claimant, reviewer):
    bounty.claim(claimant)
    bounty.submit(claimant)
    bounty.approve(reviewer)
    snap = _snapshot(bounty)

    for call in (
        lambda: bounty.claim(claimant),
        lambda: bounty.submit(claimant),
        lambda: bounty.approve(reviewer),
        lambda: bounty.reject(reviewer),
    ):
        with pytest.raises(InvalidTransition):
            call()

    assert _snapshot(bounty) == snap


# --- is_claim_expired ----------------------------------------------

def test_is_claim_expired_true_when_window_passed(bounty, claimant):
    bounty.claim(claimant)
    bounty.claim_expires_at = timezone.now() - timedelta(seconds=1)
    assert bounty.is_claim_expired is True


def test_is_claim_expired_boundary_now_counts_as_expired(bounty, claimant):
    bounty.claim(claimant)
    frozen = timezone.now()
    bounty.claim_expires_at = frozen
    # <= now: equal instant is expired
    assert bounty.claim_expires_at <= timezone.now()
    assert bounty.is_claim_expired is True


def test_is_claim_expired_false_when_future(bounty, claimant):
    bounty.claim(claimant)
    assert bounty.is_claim_expired is False


def test_is_claim_expired_false_when_not_claimed(bounty, claimant):
    bounty.claim(claimant)
    bounty.submit(claimant)
    bounty.claim_expires_at = timezone.now() - timedelta(hours=1)
    assert bounty.is_claim_expired is False


def test_str_includes_title(bounty):
    assert "Mow the lawn" in str(bounty)
