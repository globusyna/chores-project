"""Submit action / HTMX endpoint (tasks.md #13)."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from chores.models import Bounty

pytestmark = pytest.mark.django_db

Status = Bounty.Status


@pytest.fixture
def child(django_user_model):
    return django_user_model.objects.create_user(username="kid", password="pw")


@pytest.fixture
def other(django_user_model):
    return django_user_model.objects.create_user(username="kid2", password="pw")


@pytest.fixture
def bounty():
    return Bounty.objects.create(title="Fold laundry", point_value=4)


def _url(pk):
    return reverse("dashboard:submit_bounty", args=[pk])


def test_claimant_submits_and_gets_the_row_fragment(client, child, bounty):
    bounty.claim(child)
    client.force_login(child)

    response = client.post(_url(bounty.pk))

    assert response.status_code == 200
    body = response.content.decode()
    assert body.strip().startswith("<li")
    assert "<html" not in body
    bounty.refresh_from_db()
    assert bounty.status == Status.PENDING_REVIEW
    assert bounty.submitted_at is not None


def test_other_users_bounty_is_forbidden(client, child, other, bounty):
    bounty.claim(other)
    client.force_login(child)

    response = client.post(_url(bounty.pk))

    assert response.status_code == 403
    bounty.refresh_from_db()
    assert bounty.status == Status.CLAIMED


def test_submit_on_open_is_409(client, child, bounty):
    client.force_login(child)

    assert client.post(_url(bounty.pk)).status_code == 409


def test_submit_twice_second_is_409(client, child, bounty):
    bounty.claim(child)
    client.force_login(child)

    assert client.post(_url(bounty.pk)).status_code == 200
    assert client.post(_url(bounty.pk)).status_code == 409


def test_anonymous_is_redirected_to_login(client, bounty):
    response = client.post(_url(bounty.pk))

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_get_is_405(client, child, bounty):
    client.force_login(child)

    assert client.get(_url(bounty.pk)).status_code == 405


def test_missing_bounty_is_404(client, child):
    client.force_login(child)

    assert client.post(_url(999999)).status_code == 404


def test_expired_claim_is_reverted_to_open_and_rejected(client, child, bounty):
    bounty.claim(child)
    Bounty.objects.filter(pk=bounty.pk).update(
        claim_expires_at=timezone.now() - timedelta(minutes=1)
    )
    client.force_login(child)

    response = client.post(_url(bounty.pk))

    assert response.status_code == 409
    bounty.refresh_from_db()
    assert bounty.status == Status.OPEN
    assert bounty.claimed_by is None
    assert bounty.claimed_at is None
    assert bounty.claim_expires_at is None
    assert 'data-status="OPEN"' in response.content.decode()
