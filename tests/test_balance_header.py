"""Points balance header component (tasks.md #20)."""

import pytest
from django.urls import reverse

from accounts.models import Profile
from chores.models import Bounty
from ledger.models import PointTransaction
from ledger.services import record_transaction
from store.models import Perk, Purchase

pytestmark = pytest.mark.django_db


def _user(django_user_model, username, role=Profile.Role.CHILD):
    user = django_user_model.objects.create_user(username=username, password="pw")
    user.profile.role = role
    user.profile.save()
    return user


def test_authenticated_page_shows_the_balance_element_with_the_number(
    client, django_user_model
):
    user = _user(django_user_model, "kid")
    record_transaction(user, 37, PointTransaction.Reason.ADJUSTMENT)
    client.force_login(user)

    body = client.get(reverse("dashboard:board")).content.decode()

    assert 'id="points-balance"' in body
    assert "37 pts" in body
    assert "hx-swap-oob" not in body  # full page: plain element, no OOB


def test_anonymous_page_has_no_balance_element(client):
    body = client.get(reverse("dashboard:home")).content.decode()

    assert 'id="points-balance"' not in body


def test_approve_response_carries_the_oob_balance_partial(client, django_user_model):
    parent = _user(django_user_model, "mum", Profile.Role.PARENT)
    child = _user(django_user_model, "kid")
    bounty = Bounty.objects.create(title="Dishes", point_value=9)
    bounty.claim(child)
    bounty.submit(child)
    client.force_login(parent)

    response = client.post(reverse("dashboard:approve_bounty", args=[bounty.pk]))

    body = response.content.decode()
    assert 'id="points-balance"' in body
    assert 'hx-swap-oob="true"' in body
    # the child's balance really moved (full-page render for the child)
    child.profile.refresh_from_db()
    assert child.profile.points_balance == 9
    client.force_login(child)
    assert "9 pts" in client.get(reverse("dashboard:board")).content.decode()


def test_purchase_response_carries_the_oob_balance_partial(client, django_user_model):
    user = _user(django_user_model, "kid")
    Profile.objects.filter(user=user).update(points_balance=50)
    perk = Perk.objects.create(title="Snack", point_cost=10)
    client.force_login(user)

    response = client.post(reverse("dashboard:buy_perk", args=[perk.pk]))

    body = response.content.decode()
    assert 'id="points-balance"' in body
    assert 'hx-swap-oob="true"' in body


def test_fulfill_response_carries_the_oob_balance_partial(client, django_user_model):
    parent = _user(django_user_model, "mum", Profile.Role.PARENT)
    buyer = _user(django_user_model, "kid")
    Profile.objects.filter(user=buyer).update(points_balance=50)
    perk = Perk.objects.create(title="Snack", point_cost=10)
    purchase = Purchase.objects.create(perk=perk, user=buyer)
    client.force_login(parent)

    response = client.post(
        reverse("dashboard:fulfill_purchase", args=[purchase.pk])
    )

    body = response.content.decode()
    assert 'id="points-balance"' in body
    assert 'hx-swap-oob="true"' in body
    buyer.profile.refresh_from_db()
    assert buyer.profile.points_balance == 40
