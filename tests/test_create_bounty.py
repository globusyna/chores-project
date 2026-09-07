"""Ad-hoc bounty creation form (tasks.md #15)."""

import pytest
from django.urls import reverse

from accounts.models import Profile
from chores.models import Bounty

pytestmark = pytest.mark.django_db

URL = reverse("dashboard:create_bounty")


def _user(django_user_model, username, role):
    user = django_user_model.objects.create_user(username=username, password="pw")
    user.profile.role = role
    user.profile.save()
    return user


@pytest.fixture
def parent(django_user_model):
    return _user(django_user_model, "mum", Profile.Role.PARENT)


@pytest.fixture
def child(django_user_model):
    return _user(django_user_model, "kid", Profile.Role.CHILD)


def test_parent_get_renders_the_form(client, parent):
    client.force_login(parent)

    response = client.get(URL)

    assert response.status_code == 200
    assert b'name="title"' in response.content
    assert b'name="point_value"' in response.content


def test_parent_valid_post_creates_open_bounty_and_redirects(client, parent):
    client.force_login(parent)

    response = client.post(
        URL, {"title": "Rake leaves", "description": "Front yard", "point_value": 12}
    )

    assert response.status_code == 302
    assert response.url == reverse("dashboard:board")
    bounty = Bounty.objects.get()
    assert bounty.status == Bounty.Status.OPEN
    assert bounty.created_by == parent
    assert bounty.source_template is None
    assert bounty.point_value == 12


def test_blank_title_re_renders_with_errors_and_creates_nothing(client, parent):
    client.force_login(parent)

    response = client.post(URL, {"title": "", "point_value": 5})

    assert response.status_code == 200
    assert Bounty.objects.count() == 0
    assert b"errorlist" in response.content or b"This field is required" in response.content


def test_point_value_below_one_is_rejected(client, parent):
    client.force_login(parent)

    response = client.post(URL, {"title": "Freebie", "point_value": 0})

    assert response.status_code == 200
    assert Bounty.objects.count() == 0


def test_child_get_is_403(client, child):
    client.force_login(child)

    assert client.get(URL).status_code == 403


def test_child_post_is_403_and_creates_nothing(client, child):
    client.force_login(child)

    response = client.post(URL, {"title": "Sneaky", "point_value": 5})

    assert response.status_code == 403
    assert Bounty.objects.count() == 0


def test_anonymous_is_redirected_to_login(client):
    response = client.get(URL)

    assert response.status_code == 302
    assert "/accounts/login/" in response.url
