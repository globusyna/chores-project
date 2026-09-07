"""Weekly reset management command (tasks.md #16)."""

from io import StringIO

import pytest
from django.core.management import call_command

from chores.models import Bounty, ChoreTemplate

pytestmark = pytest.mark.django_db


def _run():
    out = StringIO()
    call_command("reset_weekly_board", stdout=out)
    return out.getvalue()


@pytest.fixture
def templates():
    a = ChoreTemplate.objects.create(
        title="Dishes", description="After dinner", default_point_value=5
    )
    b = ChoreTemplate.objects.create(title="Trash", default_point_value=3)
    inactive = ChoreTemplate.objects.create(
        title="Seasonal", default_point_value=9, active=False
    )
    return a, b, inactive


def test_spawns_one_open_bounty_per_active_template(templates):
    a, b, inactive = templates

    output = _run()

    bounties = Bounty.objects.all()
    assert bounties.count() == 2
    assert {x.source_template_id for x in bounties} == {a.id, b.id}
    for bounty in bounties:
        assert bounty.status == Bounty.Status.OPEN
        assert bounty.created_by is None
        assert bounty.point_value == bounty.source_template.default_point_value
        assert bounty.title == bounty.source_template.title
        assert bounty.description == bounty.source_template.description
    assert "2" in output


def test_inactive_template_never_spawns(templates):
    _, _, inactive = templates

    _run()

    assert not Bounty.objects.filter(source_template=inactive).exists()


def test_second_run_adds_another_set_without_skipping_or_erroring(templates):
    _run()
    _run()

    assert Bounty.objects.count() == 4


def test_no_active_templates_creates_nothing_and_exits_cleanly():
    ChoreTemplate.objects.create(
        title="Off", default_point_value=1, active=False
    )

    output = _run()

    assert Bounty.objects.count() == 0
    assert "0" in output
