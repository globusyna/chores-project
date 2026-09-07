"""Parent fulfilment queue & fulfill action (tasks.md #19)."""

import pytest
from django.urls import reverse

from accounts.models import Profile
from ledger.models import PointTransaction
from store.models import Perk, Purchase

pytestmark = pytest.mark.django_db

QUEUE = reverse("dashboard:fulfilment_queue")


def _user(django_user_model, username, role):
    user = django_user_model.objects.create_user(username=username, password="pw")
    user.profile.role = role
    user.profile.save()
    return user


@pytest.fixture
def parent(django_user_model):
    return _user(django_user_model, "mum", Profile.Role.PARENT)


@pytest.fixture
def buyer(django_user_model):
    return _user(django_user_model, "kid", Profile.Role.CHILD)


@pytest.fixture
def perk():
    return Perk.objects.create(title="Ice cream", point_cost=8)


@pytest.fixture
def locked(perk, buyer):
    return Purchase.objects.create(perk=perk, user=buyer)


def _set_balance(user, amount):
    Profile.objects.filter(user=user).update(points_balance=amount)


def _fulfill(pk):
    return reverse("dashboard:fulfill_purchase", args=[pk])


# --- queue -------------------------------------------------------

def test_queue_lists_only_locked(client, parent, buyer, perk):
    locked = Purchase.objects.create(perk=perk, user=buyer)
    done = Purchase.objects.create(perk=perk, user=buyer)
    done.fulfill(parent)

    client.force_login(parent)
    body = client.get(QUEUE).content.decode()

    assert f'id="purchase-{locked.pk}"' in body
    assert f'id="purchase-{done.pk}"' not in body
    assert "kid" in body and "Ice cream" in body and "8 pts" in body


def test_child_cannot_see_the_queue(client, buyer):
    client.force_login(buyer)

    assert client.get(QUEUE).status_code == 403


# --- fulfill -----------------------------------------------------

def test_parent_fulfils_and_debits_once(client, parent, buyer, perk, locked):
    _set_balance(buyer, 20)
    client.force_login(parent)

    response = client.post(_fulfill(locked.pk))

    assert response.status_code == 200
    locked.refresh_from_db()
    assert locked.status == Purchase.Status.FULFILLED
    assert locked.fulfilled_by == parent
    assert locked.fulfilled_at is not None

    txns = PointTransaction.objects.filter(related_purchase=locked)
    assert txns.count() == 1
    txn = txns.get()
    assert txn.user == buyer
    assert txn.amount == -8
    assert txn.reason == PointTransaction.Reason.PERK_DEBIT

    buyer.profile.refresh_from_db()
    assert buyer.profile.points_balance == 12


def test_double_fulfill_is_409_and_debits_once(client, parent, buyer, locked):
    _set_balance(buyer, 20)
    client.force_login(parent)

    assert client.post(_fulfill(locked.pk)).status_code == 200
    assert client.post(_fulfill(locked.pk)).status_code == 409

    assert PointTransaction.objects.filter(related_purchase=locked).count() == 1
    buyer.profile.refresh_from_db()
    assert buyer.profile.points_balance == 12


def test_child_fulfill_is_403_and_nothing_changes(client, buyer, locked):
    client.force_login(buyer)

    response = client.post(_fulfill(locked.pk))

    assert response.status_code == 403
    locked.refresh_from_db()
    assert locked.status == Purchase.Status.LOCKED
    assert PointTransaction.objects.count() == 0


def test_balance_may_go_negative(client, parent, buyer, locked):
    _set_balance(buyer, 0)
    client.force_login(parent)

    assert client.post(_fulfill(locked.pk)).status_code == 200
    buyer.profile.refresh_from_db()
    assert buyer.profile.points_balance == -8


def test_get_is_405(client, parent, locked):
    client.force_login(parent)

    assert client.get(_fulfill(locked.pk)).status_code == 405


def test_anonymous_is_redirected(client, locked):
    response = client.post(_fulfill(locked.pk))

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_missing_purchase_is_404(client, parent):
    client.force_login(parent)

    assert client.post(_fulfill(999999)).status_code == 404
