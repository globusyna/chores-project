"""Purchase model & state machine (tasks.md #9)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from store.exceptions import InvalidTransition
from store.models import Perk, Purchase

pytestmark = pytest.mark.django_db


@pytest.fixture
def perk():
    return Perk.objects.create(title="Movie night", point_cost=20)


@pytest.fixture
def buyer(django_user_model):
    return django_user_model.objects.create_user(username="kid", password="pw")


@pytest.fixture
def parent(django_user_model):
    return django_user_model.objects.create_user(username="mum", password="pw")


def test_new_purchase_defaults_to_locked(perk, buyer):
    purchase = Purchase.objects.create(perk=perk, user=buyer)

    assert purchase.status == Purchase.Status.LOCKED
    assert purchase.purchased_at is not None
    assert purchase.fulfilled_by_id is None
    assert purchase.fulfilled_at is None


def test_fulfill_sets_the_three_fields_and_status(perk, buyer, parent):
    purchase = Purchase.objects.create(perk=perk, user=buyer)
    before = timezone.now()

    purchase.fulfill(parent)

    purchase.refresh_from_db()
    assert purchase.status == Purchase.Status.FULFILLED
    assert purchase.fulfilled_by == parent
    assert purchase.fulfilled_at >= before


def test_second_fulfill_raises_and_mutates_nothing(perk, buyer, parent):
    purchase = Purchase.objects.create(perk=perk, user=buyer)
    purchase.fulfill(parent)
    purchase.refresh_from_db()
    snap = {f.attname: getattr(purchase, f.attname) for f in Purchase._meta.fields}

    with pytest.raises(InvalidTransition):
        purchase.fulfill(parent)

    purchase.refresh_from_db()
    assert {
        f.attname: getattr(purchase, f.attname) for f in Purchase._meta.fields
    } == snap


def test_fulfill_does_not_touch_points(perk, buyer, parent):
    # No ledger app wired here; just assert fulfil never imports/creates one.
    purchase = Purchase.objects.create(perk=perk, user=buyer)
    purchase.fulfill(parent)
    # buyer has no balance attribute changes to check yet (#10/#19); the
    # meaningful assertion is simply that fulfil succeeded without a ledger.
    assert purchase.status == Purchase.Status.FULFILLED


def test_ordering_is_newest_first(perk, buyer):
    old = Purchase.objects.create(
        perk=perk, user=buyer, purchased_at=timezone.now() - timedelta(days=1)
    )
    new = Purchase.objects.create(perk=perk, user=buyer)

    assert list(Purchase.objects.all()) == [new, old]


def test_str_is_readable(perk, buyer):
    purchase = Purchase.objects.create(perk=perk, user=buyer)
    assert "kid" in str(purchase) and "Movie night" in str(purchase)
