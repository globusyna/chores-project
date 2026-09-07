"""Perk store browsing & purchase action (tasks.md #18)."""

import pytest
from django.urls import reverse

from accounts.models import Profile
from store.models import Perk, Purchase

pytestmark = pytest.mark.django_db

STORE = reverse("dashboard:store")


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="kid", password="pw")


def _set_balance(user, amount):
    Profile.objects.filter(user=user).update(points_balance=amount)


def _buy(pk):
    return reverse("dashboard:buy_perk", args=[pk])


def test_anonymous_is_redirected_to_login(client):
    response = client.get(STORE)

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_store_lists_active_perks_and_balance(client, user):
    Perk.objects.create(title="Movie night", description="Pick the film", point_cost=20)
    Perk.objects.create(title="Retired perk", point_cost=5, active=False)
    _set_balance(user, 42)
    client.force_login(user)

    body = client.get(STORE).content.decode()

    assert "Movie night" in body
    assert "Pick the film" in body
    assert "20 pts" in body
    assert "42 points" in body
    assert "Retired perk" not in body


def test_buy_with_enough_points_creates_locked_purchase(client, user):
    perk = Perk.objects.create(title="Ice cream", point_cost=10)
    _set_balance(user, 10)
    client.force_login(user)

    response = client.post(_buy(perk.pk))

    assert response.status_code == 200
    body = response.content.decode()
    assert body.strip().startswith("<li")
    purchase = Purchase.objects.get()
    assert purchase.user == user
    assert purchase.perk == perk
    assert purchase.status == Purchase.Status.LOCKED
    # points are not debited until fulfilment (#19)
    user.profile.refresh_from_db()
    assert user.profile.points_balance == 10


def test_buy_without_enough_points_is_rejected_with_a_message(client, user):
    perk = Perk.objects.create(title="Big trip", point_cost=100)
    _set_balance(user, 30)
    client.force_login(user)

    response = client.post(_buy(perk.pk))

    assert response.status_code == 200
    assert Purchase.objects.count() == 0
    assert b"Not enough points" in response.content


def test_buy_inactive_perk_is_404(client, user):
    perk = Perk.objects.create(title="Gone", point_cost=1, active=False)
    _set_balance(user, 100)
    client.force_login(user)

    assert client.post(_buy(perk.pk)).status_code == 404
    assert Purchase.objects.count() == 0


def test_buy_missing_perk_is_404(client, user):
    client.force_login(user)

    assert client.post(_buy(999999)).status_code == 404


def test_get_on_buy_is_405(client, user):
    perk = Perk.objects.create(title="Snack", point_cost=1)
    client.force_login(user)

    assert client.get(_buy(perk.pk)).status_code == 405


def test_anonymous_buy_is_redirected(client):
    perk = Perk.objects.create(title="Snack", point_cost=1)

    response = client.post(_buy(perk.pk))

    assert response.status_code == 302
    assert "/accounts/login/" in response.url
