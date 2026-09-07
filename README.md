# Household Chore Bounty Board

A small server-rendered **Django + HTMX** app for running a household chore
economy:

- **Parents** post chores as point-valued *bounties* (from weekly templates
  or ad hoc) and review completed work.
- **Children** claim a bounty (a 2-hour window), mark it done, and earn its
  points once a parent approves.
- Points are spent in a **perk store**; a parent fulfils the purchase and
  the points are debited.

Every point movement is recorded in an append-only ledger, and each
account's balance is a cached mirror of that ledger.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management
- SQLite (bundled with Python — no separate database to install)

## Setup & run

```sh
uv sync                                   # install dependencies
cp .env.example .env                       # then set DJANGO_SECRET_KEY (the file shows how to generate one) DONE
uv run python manage.py migrate            # create the SQLite database
uv run python manage.py runserver          # http://127.0.0.1:8000/
```

`DJANGO_SECRET_KEY` is required — the app refuses to start without it.
`config/settings.py` auto-loads `.env`, so `manage.py` and the test suite
both pick it up.

Create an admin user for the Django admin (`/admin/`) with
`uv run python manage.py createsuperuser`.

## Seeing the board

`http://127.0.0.1:8000/` is just a placeholder page ("the board is being
built"). The real bounty board lives at **`/board/`** and needs a login.

1. Seed some data and accounts (see [Development mode](#development-mode)):

   ```sh
   uv run python manage.py seed_dev
   ```

2. Open **`http://127.0.0.1:8000/board/`** — you'll be redirected to the
   login page.
3. Log in as `test_user` / `test_password` (or `child` / `child-password`,
   or `parent` / `parent-password`).
4. Use the header nav: **Board** and **Store** for everyone; **New
   bounty**, **Review queue** and **Fulfilment** also show for `parent`.

Without `seed_dev`, `/board/` renders an empty state — add chores as
`parent` via **New bounty**, or run `reset_weekly_board` after creating
templates in `/admin/`.

## Development mode

`DEBUG` is `True` by default in `config/settings.py`, so `runserver` gives
you auto-reload and full error pages out of the box.

Seed a ready-to-use demo — a few chore templates and perks, two OPEN
bounties, and a parent and child account:

```sh
uv run python manage.py seed_dev
```

`seed_dev` is **dev only** (it errors out when `DEBUG=False`) and is safe
to run repeatedly. It seeds these logins:

| Role   | Username    | Password          |
|--------|-------------|-------------------|
| Parent | `parent`    | `parent-password` |
| Child  | `child`     | `child-password`  |
| Child  | `test_user` | `test_password`   |

`test_user` is a plain account for poking at the login flow; promote it in
the admin if you need parent access.

Balances start at 0; the command never writes ledger rows directly.

## Tests

```sh
uv run pytest                     # whole suite
uv run pytest tests/test_home.py  # a single file
```

## Scheduled commands (cron in production)

- `reset_weekly_board` — spawn this week's bounties from active templates
  (weekly, e.g. Sunday 00:00).
- `sweep_expired_claims` — return expired unfinished claims to the board
  (about every 5 minutes; the board view also does this lazily).

## Docs

`_docs/` holds the plan, architecture, task backlog, and team process;
`AGENTS.md` lists the day-to-day commands.
