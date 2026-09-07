"""Claim-expiry sweep: command + lazy board check (tasks.md #17)."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from chores.models import Bounty

pytestmark = pytest.mark.django_db

Status = Bounty.Status


@pytest.fixture
def child(django_user_model):
    return django_user_model.objects.create_user(username="kid", password="pw")


def _expire(bounty, when=None):
    Bounty.objects.filter(pk=bounty.pk).update(
        claim_expires_at=when or (timezone.now() - timedelta(minutes=1))
    )
    bounty.refresh_from_db()


def _sweep():
    out = StringIO()
    call_command("sweep_expired_claims", stdout=out)
    return out.getvalue()


def test_shared_revert_lives_on_the_manager():
    assert hasattr(Bounty.objects, "release_expired")


def test_command_reverts_expired_claim_and_leaves_others_alone(child):
    expired = Bounty.objects.create(title="Expired", point_value=5)
    expired.claim(child)
    _expire(expired)

    fresh = Bounty.objects.create(title="Fresh", point_value=5)
    fresh.claim(child)

    submitted = Bounty.objects.create(title="Submitted", point_value=5)
    submitted.claim(child)
    submitted.submit(child)
    _expire(submitted)  # past expiry but already PENDING_REVIEW

    _sweep()

    expired.refresh_from_db()
    assert expired.status == Status.OPEN
    assert expired.claimed_by is None
    assert expired.claimed_at is None
    assert expired.claim_expires_at is None

    fresh.refresh_from_db()
    assert fresh.status == Status.CLAIMED
    assert fresh.claimed_by == child

    submitted.refresh_from_db()
    assert submitted.status == Status.PENDING_REVIEW


def test_boundary_expiry_equal_to_now_counts_as_expired(child):
    bounty = Bounty.objects.create(title="Edge", point_value=5)
    bounty.claim(child)
    _expire(bounty, when=timezone.now())

    _sweep()

    bounty.refresh_from_db()
    assert bounty.status == Status.OPEN


def test_command_is_a_clean_no_op_when_nothing_expired(child):
    bounty = Bounty.objects.create(title="Fine", point_value=5)
    bounty.claim(child)

    out1 = _sweep()
    out2 = _sweep()

    bounty.refresh_from_db()
    assert bounty.status == Status.CLAIMED
    assert "0" in out1 and "0" in out2


def test_board_view_reverts_expired_claim_lazily(client, child):
    bounty = Bounty.objects.create(title="Lazy", point_value=5)
    bounty.claim(child)
    _expire(bounty)

    client.force_login(child)
    body = client.get(reverse("dashboard:board")).content.decode()

    bounty.refresh_from_db()
    assert bounty.status == Status.OPEN
    assert f'id="bounty-{bounty.pk}"' in body
    assert 'data-status="OPEN"' in body
