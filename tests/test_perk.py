"""Perk model (tasks.md #8)."""

import pytest
from django.core.exceptions import ValidationError

from store.models import Perk

pytestmark = pytest.mark.django_db


def test_perk_is_created_with_active_default_true():
    perk = Perk.objects.create(title="Movie night", point_cost=20)

    assert perk.pk is not None
    assert perk.active is True
    assert perk.description == ""


def test_str_returns_the_title():
    assert str(Perk(title="Extra screen time", point_cost=5)) == "Extra screen time"


def test_zero_point_cost_is_rejected():
    with pytest.raises(ValidationError):
        Perk(title="Freebie", point_cost=0).full_clean()


def test_ordering_is_by_title():
    Perk.objects.create(title="Zoo trip", point_cost=1)
    Perk.objects.create(title="Ada's choice", point_cost=1)

    assert list(Perk.objects.values_list("title", flat=True)) == [
        "Ada's choice",
        "Zoo trip",
    ]
