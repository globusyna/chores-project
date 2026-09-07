"""Profile model & roles (tasks.md #4)."""

import pytest
from django.urls import reverse

from accounts.models import Profile

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="alice", password="pw")


def test_new_user_gets_exactly_one_child_profile(user):
    assert Profile.objects.filter(user=user).count() == 1
    assert user.profile.role == Profile.Role.CHILD


def test_superuser_creation_path_also_gets_a_profile(django_user_model):
    admin = django_user_model.objects.create_superuser(
        username="root", password="pw", email="root@example.com"
    )

    assert admin.profile.role == Profile.Role.CHILD


def test_resaving_user_does_not_duplicate_or_reset_role(user):
    user.profile.role = Profile.Role.PARENT
    user.profile.save()

    user.first_name = "Alice"
    user.save()

    user.refresh_from_db()
    assert Profile.objects.filter(user=user).count() == 1
    assert user.profile.role == Profile.Role.PARENT


def test_deleting_user_cascades_to_its_profile_only(user, django_user_model):
    other = django_user_model.objects.create_user(username="bob", password="pw")
    doomed_profile_pk = user.profile.pk

    user.delete()

    assert not Profile.objects.filter(pk=doomed_profile_pk).exists()
    assert Profile.objects.filter(user=other).count() == 1


def test_str_is_readable(user):
    assert str(user.profile) == "alice (Child)"

    user.profile.role = Profile.Role.PARENT
    assert str(user.profile) == "alice (Parent)"


def test_admin_promotion_to_parent_persists(client, django_user_model, user):
    admin = django_user_model.objects.create_superuser(
        username="root", password="pw", email="root@example.com"
    )
    client.force_login(admin)

    response = client.post(
        reverse("admin:accounts_profile_change", args=[user.profile.pk]),
        {"user": user.pk, "role": Profile.Role.PARENT, "_save": "Save"},
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.profile.role == Profile.Role.PARENT


def test_profile_inline_shows_on_user_admin_page(client, django_user_model, user):
    admin = django_user_model.objects.create_superuser(
        username="root", password="pw", email="root@example.com"
    )
    client.force_login(admin)

    response = client.get(reverse("admin:auth_user_change", args=[user.pk]))

    assert response.status_code == 200
    assert b'name="profile-0-role"' in response.content
