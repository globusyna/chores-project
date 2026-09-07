"""ChoreTemplate model (tasks.md #6)."""

import pytest
from django.core.exceptions import ValidationError

from chores.models import ChoreTemplate

pytestmark = pytest.mark.django_db


def test_template_is_created_with_active_default_true():
    template = ChoreTemplate.objects.create(
        title="Take out the bins", default_point_value=5
    )

    assert template.pk is not None
    assert template.active is True
    assert template.description == ""


def test_str_returns_the_title():
    template = ChoreTemplate(title="Wash the dishes", default_point_value=3)

    assert str(template) == "Wash the dishes"


def test_zero_point_value_is_rejected():
    template = ChoreTemplate(title="Freebie", default_point_value=0)

    with pytest.raises(ValidationError):
        template.full_clean()


def test_ordering_is_by_title():
    ChoreTemplate.objects.create(title="Zebra duty", default_point_value=1)
    ChoreTemplate.objects.create(title="Apple duty", default_point_value=1)

    titles = list(ChoreTemplate.objects.values_list("title", flat=True))
    assert titles == ["Apple duty", "Zebra duty"]
