"""Parent-only / child-only access control helpers (tasks.md #5)."""

import pytest
from django.http import HttpResponse
from django.urls import include, path

from accounts.models import Profile
from accounts.permissions import child_required, parent_required


@parent_required
def _parent_only_view(request):
    return HttpResponse("parent ok")


@child_required
def _child_only_view(request):
    return HttpResponse("child ok")


urlpatterns = [
    path("parent-only/", _parent_only_view),
    path("child-only/", _child_only_view),
    # so LOGIN_URL='login' still reverses under this test urlconf
    path("accounts/", include("django.contrib.auth.urls")),
]

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.test_permissions")]


def _make(django_user_model, username, role=None):
    user = django_user_model.objects.create_user(username=username, password="pw")
    if role is not None:
        user.profile.role = role
        user.profile.save()
    return user


def test_anonymous_is_redirected_to_login(client):
    response = client.get("/parent-only/")

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_authenticated_child_gets_403_from_parent_view(client, django_user_model):
    client.force_login(_make(django_user_model, "kid", Profile.Role.CHILD))

    response = client.get("/parent-only/")

    assert response.status_code == 403


def test_authenticated_parent_passes_through(client, django_user_model):
    client.force_login(_make(django_user_model, "mum", Profile.Role.PARENT))

    response = client.get("/parent-only/")

    assert response.status_code == 200
    assert response.content == b"parent ok"


def test_user_without_profile_is_treated_as_non_parent(client, django_user_model):
    user = _make(django_user_model, "orphan")
    user.profile.delete()
    client.force_login(user)

    response = client.get("/parent-only/")

    assert response.status_code == 403


def test_child_required_mirrors_parent_required(client, django_user_model):
    client.force_login(_make(django_user_model, "kid2", Profile.Role.CHILD))
    assert client.get("/child-only/").status_code == 200

    client.force_login(_make(django_user_model, "dad", Profile.Role.PARENT))
    assert client.get("/child-only/").status_code == 403

    client.logout()
    assert client.get("/child-only/").status_code == 302


def test_module_docstring_shows_a_usage_snippet():
    import accounts.permissions as perms

    assert "@parent_required" in perms.__doc__
    assert "@child_required" in perms.__doc__
