"""Username/password authentication (tasks.md #3)."""

import pytest
from django.urls import reverse

USERNAME = "alice"
PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username=USERNAME, password=PASSWORD
    )


def test_login_url_is_routed_with_stable_name():
    assert reverse("login") == "/accounts/login/"
    assert reverse("logout") == "/accounts/logout/"


def test_login_page_renders_for_anonymous(client):
    response = client.get(reverse("login"))

    assert response.status_code == 200
    assert b'name="username"' in response.content
    assert b'name="password"' in response.content


@pytest.mark.django_db
def test_valid_credentials_redirect_and_authenticate(client, user):
    response = client.post(
        reverse("login"), {"username": USERNAME, "password": PASSWORD}
    )

    assert response.status_code == 302
    assert response.url == "/"  # LOGIN_REDIRECT_URL -> dashboard:home
    assert client.session.get("_auth_user_id") == str(user.pk)


@pytest.mark.django_db
def test_invalid_credentials_stay_on_page_with_error(client, user):
    response = client.post(
        reverse("login"), {"username": USERNAME, "password": "wrong"}
    )

    assert response.status_code == 200
    assert b"didn&#x27;t match" in response.content or b"didn't match" in response.content
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_login_honours_next_parameter(client, user):
    response = client.post(
        f"{reverse('login')}?next=/admin/",
        {"username": USERNAME, "password": PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == "/admin/"


@pytest.mark.django_db
def test_logout_is_post_only_and_clears_the_session(client, user):
    client.force_login(user)
    assert "_auth_user_id" in client.session

    get_response = client.get(reverse("logout"))
    assert get_response.status_code == 405  # Django 6 removed GET logout
    assert "_auth_user_id" in client.session

    post_response = client.post(reverse("logout"))
    assert post_response.status_code == 302
    assert post_response.url == "/"  # LOGOUT_REDIRECT_URL
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_base_page_reflects_auth_state(client, user):
    anon = client.get(reverse("dashboard:home"))
    assert b'href="/accounts/login/"' in anon.content
    assert b"Signed in as" not in anon.content

    client.force_login(user)
    authed = client.get(reverse("dashboard:home"))
    assert b"Signed in as alice" in authed.content
    assert b'action="/accounts/logout/"' in authed.content
