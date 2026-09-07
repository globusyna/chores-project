"""Read-only bounty board view (tasks.md #11)."""

import pytest
from django.urls import reverse

from chores.models import Bounty

pytestmark = pytest.mark.django_db

Status = Bounty.Status


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(username="viewer", password="pw")


def test_anonymous_is_redirected_to_login(client):
    response = client.get(reverse("dashboard:board"))

    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_authenticated_user_gets_200(client, user):
    client.force_login(user)

    assert client.get(reverse("dashboard:board")).status_code == 200


def test_empty_board_renders_friendly_state(client, user):
    client.force_login(user)

    response = client.get(reverse("dashboard:board"))

    assert response.status_code == 200
    assert b"board-empty" in response.content


def test_open_and_claimed_show_but_approved_does_not(client, user, django_user_model):
    claimant = django_user_model.objects.create_user(username="kid", password="pw")
    Bounty.objects.create(title="Sweep porch", point_value=5)
    claimed = Bounty.objects.create(title="Walk dog", point_value=8)
    claimed.claim(claimant)
    Bounty.objects.create(title="Old chore", point_value=9, status=Status.APPROVED)

    client.force_login(user)
    body = client.get(reverse("dashboard:board")).content.decode()

    assert "Sweep porch" in body
    assert "Walk dog" in body
    assert "Claimed by kid" in body
    assert "Old chore" not in body


def test_row_has_stable_dom_id(client, user):
    bounty = Bounty.objects.create(title="Tidy shelf", point_value=2)
    client.force_login(user)

    body = client.get(reverse("dashboard:board")).content.decode()

    assert f'id="bounty-{bounty.pk}"' in body


def test_ordering_open_first_then_point_value_desc(client, user, django_user_model):
    claimant = django_user_model.objects.create_user(username="kid", password="pw")
    low = Bounty.objects.create(title="OPEN-LOW", point_value=1)
    high = Bounty.objects.create(title="OPEN-HIGH", point_value=100)
    claimed = Bounty.objects.create(title="CLAIMED-HUGE", point_value=999)
    claimed.claim(claimant)

    client.force_login(user)
    body = client.get(reverse("dashboard:board")).content.decode()

    assert body.index("OPEN-HIGH") < body.index("OPEN-LOW") < body.index("CLAIMED-HUGE")


def test_board_view_adds_no_review_controls_of_its_own(client, user):
    # #11 itself renders no actions; the claim control on OPEN rows is
    # added by the shared row partial in #12. The board view still wires
    # no approve/reject/submit logic.
    Bounty.objects.create(title="Tidy shelf", point_value=2)
    client.force_login(user)

    body = client.get(reverse("dashboard:board")).content.decode()
    main = body.split("<main>")[1].split("</main>")[0]

    assert "/submit/" not in main
    assert "/approve/" not in main
    assert "/reject/" not in main
