"""Smoke test proving the project is wired up end to end (tasks.md #1)."""


def test_home_page_returns_200(client):
    response = client.get("/")

    assert response.status_code == 200
