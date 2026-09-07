# Household Chore Bounty Board

A small Django + HTMX app: parents post chores as point bounties, children
claim and complete them, points buy perks from a store. See `_docs/` for
the plan, architecture, and task backlog, and `AGENTS.md` for the
day-to-day commands.

## Quick start

```sh
uv sync
cp .env.example .env    # then set DJANGO_SECRET_KEY (see the file)
uv run python manage.py migrate
uv run python manage.py runserver
```

## Running the tests

```sh
uv run pytest                    # whole suite
uv run pytest tests/test_home.py # one file
```

## Dev seed data

`seed_dev` populates a demo board, perks, and two accounts so the app is
usable immediately. It is **dev only** — it refuses to run when
`DEBUG=False` — and is safe to run repeatedly (everything is
`get_or_create`d).

```sh
uv run python manage.py seed_dev
```

Seeded logins:

| Role   | Username | Password          |
|--------|----------|-------------------|
| Parent | `parent` | `parent-password` |
| Child  | `child`  | `child-password`  |

Balances start at 0; the command never writes ledger rows directly.

## Scheduled commands (cron in production)

- `reset_weekly_board` — spawn this week's bounties from active templates
  (weekly, e.g. Sunday 00:00).
- `sweep_expired_claims` — return expired unfinished claims to the board
  (about every 5 minutes).
