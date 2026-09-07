"""Claim action / HTMX endpoint (tasks.md #12)."""

from datetime import timedelta

import pytest
from django.urls import reverse

from accounts.models import Profile
from chores.models import CLAIM_WINDOW, Bounty

pytestmark = pytest.mark.django_db

Status = Bounty.Status


def _user(django_user_model, username, role):
    user = django_user_model.objects.create_user(username=username, password="pw")
    user.profile.role = role
    user.profile.save()
    return user


@pytest.fixture
def child(django_user_model):
    return _user(django_user_model, "kid", Profile.Role.CHILD)


@pytest.fixture
def parent(django_user_model):
    return _user(django_user_model, "mum", Profile.Role.PARENT)


@pytest.fixture
def bounty():
    return Bounty.objects.create(title="Vacuum the hall", point_value=7)


def _url(pk):
    return reverse("dashboard:claim_bounty", args=[pk])


def test_child_claims_open_bounty_and_gets_the_row_fragment(client, child, bounty):
    client.force_login(child)

    response = client.post(_url(bounty.pk))

    assert response.status_code == 200
    body = response.content.decode()
    assert body.strip().startswith("<li")  # fragment, not a full page
    assert "<html" not in body
    assert f'id="bounty-{bounty.pk}"' in body
    assert "Claimed by kid" in body

    bounty.refresh_from_db()
    assert bounty.status == Status.CLAIMED
    assert bounty.claimed_by == child
    assert bounty.claim_expires_at == bounty.claimed_at + CLAIM_WINDOW
    assert CLAIM_WINDOW == timedelta(hours=2)


def test_parent_is_forbidden(client, parent, bounty):
    client.force_login(parent)

    response = client.post(_url(bounty.pk))

    assert response.status_code == 403
    bounty.refresh_from_db()
    assert bounty.status == Status.OPEN


def test_claiming_an_already_claimed_bounty_returns_409_fragment(
    client, child, bounty, django_user_model
):
    first = _user(django_user_model, "kid2", Profile.Role.CHILD)
    bounty.claim(first)
    client.force_login(child)

    response = client.post(_url(bounty.pk))

    assert response.status_code == 409
    assert f'id="bounty-{bounty.pk}"' in response.content.decode()
    bounty.refresh_from_db()
    assert bounty.claimed_by == first  # unchanged


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
