"""Parent review queue & approve/reject actions (tasks.md #14)."""

import pytest
from django.urls import reverse

from accounts.models import Profile
from chores.models import Bounty
from ledger.models import PointTransaction

pytestmark = pytest.mark.django_db

Status = Bounty.Status


def _user(django_user_model, username, role):
    user = django_user_model.objects.create_user(username=username, password="pw")
    user.profile.role = role
    user.profile.save()
    return user


@pytest.fixture
def parent(django_user_model):
    return _user(django_user_model, "mum", Profile.Role.PARENT)


@pytest.fixture
def child(django_user_model):
    return _user(django_user_model, "kid", Profile.Role.CHILD)


@pytest.fixture
def pending(child):
    bounty = Bounty.objects.create(title="Scrub the tub", point_value=15)
    bounty.claim(child)
    bounty.submit(child)
    return bounty


def _approve(pk):
    return reverse("dashboard:approve_bounty", args=[pk])


def _reject(pk):
    return reverse("dashboard:reject_bounty", args=[pk])


# --- queue -------------------------------------------------------------

def test_queue_lists_only_pending_review(client, parent, child):
    Bounty.objects.create(title="OPEN one", point_value=1)
    claimed = Bounty.objects.create(title="CLAIMED one", point_value=2)
    claimed.claim(child)
    pending = Bounty.objects.create(title="PENDING one", point_value=3)
    pending.claim(child)
    pending.submit(child)
    approved = Bounty.objects.create(title="APPROVED one", point_value=4)
    approved.claim(child)
    approved.submit(child)
    approved.approve(parent)

    client.force_login(parent)
    body = client.get(reverse("dashboard:review_queue")).content.decode()

    assert "PENDING one" in body
    assert "kid" in body  # claimant
    for other in ("OPEN one", "CLAIMED one", "APPROVED one"):
        assert other not in body


def test_child_cannot_see_the_queue(client, child):
    client.force_login(child)

    assert client.get(reverse("dashboard:review_queue")).status_code == 403


# --- approve ---------------------------------------------------------

def test_parent_approve_flips_state_and_awards_points_once(client, parent, child, pending):
    client.force_login(parent)

    response = client.post(_approve(pending.pk))

    assert response.status_code == 200
    pending.refresh_from_db()
    assert pending.status == Status.APPROVED
    assert pending.reviewed_by == parent

    txns = PointTransaction.objects.filter(related_bounty=pending)
    assert txns.count() == 1
    txn = txns.get()
    assert txn.user == child
    assert txn.amount == 15
    assert txn.reason == PointTransaction.Reason.BOUNTY_AWARD

    child.profile.refresh_from_db()
    assert child.profile.points_balance == 15


def test_double_approve_is_409_and_awards_once(client, parent, child, pending):
    client.force_login(parent)

    assert client.post(_approve(pending.pk)).status_code == 200
    assert client.post(_approve(pending.pk)).status_code == 409

    assert PointTransaction.objects.filter(related_bounty=pending).count() == 1
    child.profile.refresh_from_db()
    assert child.profile.points_balance == 15


def test_approve_on_non_pending_is_409(client, parent, child):
    bounty = Bounty.objects.create(title="Just claimed", point_value=5)
    bounty.claim(child)
    client.force_login(parent)

    assert client.post(_approve(bounty.pk)).status_code == 409
    assert PointTransaction.objects.count() == 0


def test_child_approve_is_403(client, child, parent, pending):
    client.force_login(child)

    assert client.post(_approve(pending.pk)).status_code == 403
    pending.refresh_from_db()
    assert pending.status == Status.PENDING_REVIEW
    assert PointTransaction.objects.count() == 0


# --- reject --------------------------------------------------------

def test_parent_reject_returns_to_claimed_without_a_ledger_row(client, parent, child, pending):
    claimed_by, claimed_at, expires = (
        pending.claimed_by,
        pending.claimed_at,
        pending.claim_expires_at,
    )
    client.force_login(parent)

    response = client.post(_reject(pending.pk), {"notes": "Missed the corners"})

    assert response.status_code == 200
    pending.refresh_from_db()
    assert pending.status == Status.CLAIMED
    assert pending.review_notes == "Missed the corners"
    assert pending.claimed_by == claimed_by
    assert pending.claimed_at == claimed_at
    assert pending.claim_expires_at == expires
    assert PointTransaction.objects.count() == 0
    child.profile.refresh_from_db()
    assert child.profile.points_balance == 0


def test_reject_without_notes_is_allowed(client, parent, pending):
    client.force_login(parent)

    assert client.post(_reject(pending.pk)).status_code == 200
    pending.refresh_from_db()
    assert pending.status == Status.CLAIMED
    assert pending.review_notes == ""


def test_child_reject_is_403(client, child, pending):
    client.force_login(child)

    assert client.post(_reject(pending.pk)).status_code == 403
    pending.refresh_from_db()
    assert pending.status == Status.PENDING_REVIEW


def test_reject_on_non_pending_is_409(client, parent, child):
    bounty = Bounty.objects.create(title="Just claimed", point_value=5)
    bounty.claim(child)
    client.force_login(parent)

    assert client.post(_reject(bounty.pk)).status_code == 409


# --- method / auth guards -----------------------------------------

def test_get_on_action_endpoints_is_405(client, parent, pending):
    client.force_login(parent)

    assert client.get(_approve(pending.pk)).status_code == 405
    assert client.get(_reject(pending.pk)).status_code == 405


def test_anonymous_is_redirected(client, pending):
    assert client.post(_approve(pending.pk)).status_code == 302
    assert client.post(_reject(pending.pk)).status_code == 302


def test_missing_bounty_is_404(client, parent):
    client.force_login(parent)

    assert client.post(_approve(999999)).status_code == 404
    assert client.post(_reject(999999)).status_code == 404
