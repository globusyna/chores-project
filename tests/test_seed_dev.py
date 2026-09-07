"""Dev seed data command (tasks.md #21)."""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import Profile
from chores.models import Bounty, ChoreTemplate
from store.models import Perk

pytestmark = pytest.mark.django_db

User = get_user_model()


def _run():
    out = StringIO()
    call_command("seed_dev", stdout=out)
    return out.getvalue()


def test_seed_creates_expected_objects(settings):
    settings.DEBUG = True

    output = _run()

    assert ChoreTemplate.objects.count() == 3
    assert Perk.objects.count() == 3
    assert Bounty.objects.filter(status=Bounty.Status.OPEN).count() == 2

    parent = User.objects.get(username="parent")
    child = User.objects.get(username="child")
    test_user = User.objects.get(username="test_user")
    assert parent.profile.role == Profile.Role.PARENT
    assert child.profile.role == Profile.Role.CHILD
    assert test_user.profile.role == Profile.Role.CHILD
    assert parent.check_password("parent-password")
    assert child.check_password("child-password")
    assert test_user.check_password("test_password")

    assert "parent" in output and "child" in output and "test_user" in output


def test_seed_is_idempotent(settings):
    settings.DEBUG = True

    _run()
    _run()

    assert (
        User.objects.filter(
            username__in=["parent", "child", "test_user"]
        ).count()
        == 3
    )
    assert ChoreTemplate.objects.count() == 3
    assert Perk.objects.count() == 3
    assert Bounty.objects.count() == 2


def test_seed_writes_no_ledger_rows_and_leaves_balances_at_zero(settings):
    settings.DEBUG = True

    _run()

    from ledger.models import PointTransaction

    assert PointTransaction.objects.count() == 0
    for profile in Profile.objects.all():
        assert profile.points_balance == 0


def test_seed_refuses_to_run_with_debug_false(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError):
        _run()

    assert User.objects.filter(username="parent").count() == 0


def test_seeded_test_user_can_log_in(settings, client):
    settings.DEBUG = True
    _run()

    response = client.post(
        "/accounts/login/",
        {"username": "test_user", "password": "test_password"},
    )

    assert response.status_code == 302
    assert client.session.get("_auth_user_id") == str(
        User.objects.get(username="test_user").pk
    )
