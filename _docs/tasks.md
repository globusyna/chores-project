# Household Chore Bounty Board - Backlog (V1)

Companion to `plan.md` and `architecture.md`. Scope is the v1 slice
only: Django + HTMX + SQLite, username/password auth, no Discord
integration (deferred to Phase 2 per `architecture.md` §6/§9 — those
tasks aren't listed here and will get their own backlog later).

Each task is groomed to the shape in `_docs/task-template.md` — Goal,
Acceptance criteria, Out of scope, Constraints, a Dependencies line, and
any open decisions. Tasks cite `plan.md` / `architecture.md` sections for
background and reference sibling tasks by number (`#N`) only to hand off
scope. Numbering reflects a sensible build order; the Dependencies line
is the real constraint.

Stack as built in #1: Django 6.1 + pytest-django, project package
`config/`, first app `dashboard/`, tests under `tests/`. Run the suite
with `uv run pytest` (see `AGENTS.md`).

---

## 1. Project Scaffolding & First Passing Test

### Goal

An empty, runnable Django project with one passing test, proving the
toolchain (Django + SQLite + pytest) works end to end. No models, auth,
or business logic.

### Status

**Done.** Implemented as `config/` (settings/urls/wsgi/asgi), app
`dashboard/` with a `home` view + template at `/`, and
`tests/test_home.py` asserting `GET /` → 200. `pyproject.toml` pins
`django>=5.2` and a `dev` group with `pytest` + `pytest-django`;
`uv run pytest` is green.

### Acceptance criteria

- [x] `uv sync` installs the project; `uv run python manage.py check`
      passes.
- [x] `dashboard` is in `INSTALLED_APPS`; DB is SQLite with default
      settings.
- [x] One test exercises a real view and asserts HTTP 200.
- [x] `uv run pytest` and `uv run pytest tests/test_home.py` both pass.

### Out of scope

- Secrets / `.gitignore` (#2), auth (#3), any domain model (#6, #7, …).

### Constraints

- Tests live under `tests/` (per `AGENTS.md`); no new dependencies
  beyond Django + pytest-django.

### Dependencies

None — this is the first task.

---

## 2. Secrets & .gitignore Setup

### Goal

Credentials and local build artifacts stay out of version control, and
`SECRET_KEY` comes from the environment rather than a literal in
`settings.py`. Background: `architecture.md` §11, §14.

### Status

**Done.** Repo-root `.gitignore` added (SQLite + `-journal`/`-wal`,
`__pycache__/`, `*.py[cod]`, `.venv/`/`venv/`, `.env`, `.pytest_cache/`,
`.DS_Store`); previously-committed `__pycache__` `.pyc` files removed
from the index. `config/settings.py` now reads `SECRET_KEY` from
`DJANGO_SECRET_KEY` and raises `ImproperlyConfigured` when it is unset or
empty — no fallback — after a dependency-free `.env` autoloader (the
recommended option) populates `os.environ` for both `manage.py` and
pytest. `.env.example` is committed with an empty `DJANGO_SECRET_KEY=`
and a generation command; `.env` is git-ignored. Covered by
`tests/test_settings_secrets.py`; `uv run pytest` is green.

### Acceptance criteria

- [ ] A repo-root `.gitignore` ignores at least: `*.sqlite3` (and
      `-journal` / `-wal`), `__pycache__/`, `*.py[cod]`, `.venv/` /
      `venv/`, `.env`, `.pytest_cache/`, `.DS_Store`.
- [ ] `git status` is clean of the SQLite file and `__pycache__` after a
      test run.
- [ ] `config/settings.py` reads `SECRET_KEY` from `DJANGO_SECRET_KEY`;
      no key literal remains in the file.
- [ ] Starting Django (or importing settings) with `DJANGO_SECRET_KEY`
      unset or empty raises `ImproperlyConfigured` with a clear message —
      no insecure fallback.
- [ ] `.env.example` is committed, lists `DJANGO_SECRET_KEY=` with no
      real value, and documents how to generate one.
- [ ] `.env` is git-ignored and not committed; `uv run pytest` still
      passes (the test path must supply the var — see decisions).

### Out of scope

- Productionising `DEBUG` / `ALLOWED_HOSTS` (no deployment task in this
  backlog yet — leave them as-is).
- The Discord webhook secret — Phase 2 (`architecture.md` §9, §11).
- Key rotation / multiple environments.

### Constraints

- `.gitignore` at the repo root. No secret values in any committed file.
- Prefer zero new dependencies (see decisions).

### Dependencies

#1.

### Open decisions

- **How the env var reaches settings + pytest.** Recommended: a tiny
  `.env` autoloader at the top of `config/settings.py` (read the file if
  present, populate `os.environ`, ~8 lines) so `manage.py` and pytest
  behave identically with no dependency. Alternatives: `uv run
  --env-file .env …` (no autoload, but pytest needs the flag too), or
  add `django-environ` / `python-dotenv` (needs sign-off per `AGENTS.md`).

---

## 3. Username/Password Authentication

### Goal

A user with an existing account can sign in and sign out. No
self-service signup — accounts are created by a parent
(`architecture.md` §6, `plan.md` §3).

### Status

**Done.** `django.contrib.auth.urls` mounted at `/accounts/`
(`login` / `logout` names). `BASE_DIR / "templates"` added to
`TEMPLATES[0]["DIRS"]` with shared `base.html` and
`registration/login.html`; the base header shows `username` + a POST
logout form when signed in, a login link when not. `LOGIN_URL`,
`LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL` set (`next` round-trips).
Logout is POST-only (GET → 405). Covered by `tests/test_auth.py`;
`uv run pytest` is green (26 passed).

### Acceptance criteria

- [ ] Django's built-in auth login/logout views are routed (e.g.
      `include("django.contrib.auth.urls")` or explicit `LoginView` /
      `LogoutView`) at stable URLs.
- [ ] A minimal `registration/login.html` renders for anonymous users
      (200).
- [ ] Valid credentials POST → redirect to `LOGIN_REDIRECT_URL` and an
      authenticated session.
- [ ] Invalid credentials POST → same page, 200, visible error, still
      anonymous.
- [ ] Logout is POST-only (Django 6.x removed GET logout): the UI uses a
      POST form, and logout clears the session and redirects.
- [ ] `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL` are set so
      `@login_required` round-trips correctly.
- [ ] The base page shows auth state minimally: username + logout form
      when signed in, a login link when not.
- [ ] Tests cover: anonymous login page 200; valid POST → redirect +
      authenticated; invalid POST → 200 + not authenticated; logout POST
      → session cleared.

### Out of scope

- Signup / registration, password reset / change, email sending.
- Discord OAuth — Phase 2 (`architecture.md` §6, §9).
- Role-aware redirects or gating — that's #5.
- Visual design beyond a bare form (`_docs/design-system.md` is empty).

### Constraints

- Use the built-in auth views; write no custom authentication logic.
- Add `BASE_DIR / "templates"` to `TEMPLATES[0]["DIRS"]` and put shared
  templates (`base.html`, `registration/`) there.
- Tests under `tests/`.

### Dependencies

#1. (Independent of #4/#5, but naturally paired with them.)

---

## 4. Profile Model & Roles

### Goal

Every Django `User` has a `Profile` recording whether they are a Parent
or a Child, so later work can gate parent-only actions (#5) and attribute
points (#10). New profiles start as `CHILD`; a parent is promoted by hand
in the Django admin. Draws on `plan.md` §3 and `architecture.md` §3,
§4, §6.

### Status

**Done.** New `accounts` app in `INSTALLED_APPS`. `Profile` =
`OneToOneField(AUTH_USER_MODEL, CASCADE, related_name="profile")` +
`role` (`TextChoices` PARENT/CHILD, default CHILD); `__str__` →
`"alice (Child)"`. A `post_save` receiver registered in
`AccountsConfig.ready()` gives every new user one CHILD profile
(`created`-guarded + `get_or_create`, so re-save neither duplicates nor
resets). `ProfileAdmin` (list `user`/`role`, `role` editable) plus a
`ProfileInline` on the User admin; migrations `0001_initial` +
`0002_backfill_profiles` (data). Covered by `tests/test_profile.py`;
`uv run pytest` green (33 passed).

### Acceptance criteria

- [ ] A new `accounts` app exists and is in `INSTALLED_APPS`
      (`architecture.md` §3).
- [ ] `Profile` model: `OneToOneField` to `settings.AUTH_USER_MODEL`,
      `on_delete=CASCADE`, `related_name="profile"`.
- [ ] `role` uses `models.TextChoices` with values `PARENT` / `CHILD`,
      `default=CHILD`.
- [ ] Creating a `User` by any path (admin, `createsuperuser`, shell,
      fixture) yields exactly one `Profile` defaulted to `CHILD`, via a
      `post_save` signal registered in `accounts/apps.py` `ready()`.
- [ ] Re-saving an existing `User` does not create a second `Profile` and
      does not reset `role`.
- [ ] Deleting a `User` deletes its `Profile` and nothing else.
- [ ] `Profile` is registered in the Django admin: a standalone list
      showing `user` and `role` with `role` editable, and an inline on
      the `User` admin so the role shows on the user page.
- [ ] Promoting to `PARENT` in the admin persists and reads back as
      `user.profile.role == Profile.Role.PARENT`.
- [ ] `__str__` is readable, e.g. `"alice (Child)"`.
- [ ] A data migration backfills `Profile` rows for any pre-existing
      users (none expected, but keeps `migrate` safe).
- [ ] Tests (`tests/`, pytest-django) cover: default role on user
      creation, no duplicate on re-save, CASCADE delete, admin promotion
      persists.

### Out of scope

- `Profile.points_balance` denormalized cache — added by #10, where it
  is written and covered by the "balance == sum of ledger" test.
- `discord_id` and any Discord / OAuth linkage — Phase 2
  (`architecture.md` §6, §9).
- The `parent_required` decorator and child queryset scoping — #5.
- Any non-admin UI for roles; self-service signup (there is none,
  `plan.md` §3).

### Constraints

- New code confined to `accounts/`; the only change outside it is
  `config/settings.py` (`INSTALLED_APPS`).
- Keep the default `django.contrib.auth` `User` — do not add a custom
  user model. Reference it as `settings.AUTH_USER_MODEL` /
  `get_user_model()`, not a hard import in model code.
- Migrations committed with the task. No new dependencies.
  `_docs/testing-guidelines.md` is currently empty — nothing extra to
  follow.

### Dependencies

#1. (#3 not required — `User` exists regardless.)

### Open decisions

- **Signal vs admin-inline-only.** Recommended: the `post_save` signal.
  Without it, shell- and fixture-created users have no `Profile` and
  `user.profile` raises.

---

## 5. Parent-Only Access Control Helper

### Goal

A reusable way to restrict a view to parent accounts. Background:
`architecture.md` §3 (the `accounts` app owns permission helpers), §6,
§11.

### Status

**Done.** `accounts/permissions.py`: `parent_required` decorator built on
`login_required` + `PermissionDenied` (anonymous → `LOGIN_URL` redirect,
authed non-parent / no-Profile → 403, parent → through). Per the open
decision, a symmetric `child_required` is added alongside, plus
`ParentRequiredMixin` / `ChildRequiredMixin` for CBVs. Module docstring
carries the usage snippet. Covered by `tests/test_permissions.py`;
`uv run pytest` green (39 passed).

### Acceptance criteria

- [ ] `parent_required` lives in `accounts` (e.g.
      `accounts/permissions.py`), usable as a decorator on function
      views; a CBV mixin is optional.
- [ ] Anonymous user → redirect to `LOGIN_URL` (same behaviour as
      `login_required`), not 403.
- [ ] Authenticated child → `HttpResponseForbidden` / raises
      `PermissionDenied` (403).
- [ ] Authenticated parent → the wrapped view runs normally.
- [ ] Authenticated user with no `Profile` → treated as non-parent (403),
      no `AttributeError` / `RelatedObjectDoesNotExist`.
- [ ] A docstring shows the usage snippet.
- [ ] Tests hit a dummy parent-only view as parent (200), child (403),
      anonymous (redirect), and no-profile user (403).

### Out of scope

- Per-object permissions / ACLs — role-based only (`architecture.md` §6).
- Per-feature child queryset scoping — applied in #12–#14, #18.

### Constraints

- Lives in `accounts`; build on `django.contrib.auth` primitives
  (`user_passes_test`, `PermissionDenied`), don't hand-roll session
  checks. No new dependencies. Tests under `tests/`.

### Dependencies

#4 (needs `Profile.role`). Pairs with #3 for the redirect.

### Open decisions

- **Companion `child_required`.** #12, #13, #18 need "child only". If
  symmetric and cheap, add `child_required` alongside here; otherwise
  those tasks do an inline `role == CHILD` check. Recommended: add it
  here.

---

## 6. Chore Template Model

### Goal

Define the recurring chores that repopulate the board each week.
Background: `architecture.md` §3 (`chores` app), §4, §8.

### Status

**Done.** New `chores` app in `INSTALLED_APPS`. `ChoreTemplate` =
`title` / `description` (blank) / `default_point_value`
(`PositiveIntegerField` + `MinValueValidator(1)`) / `active`
(default `True`); `__str__` → title, `Meta.ordering = ["title"]`.
`ChoreTemplateAdmin` lists `title` / `default_point_value` / `active`
with `active` list-editable. Migration `0001_initial`. Covered by
`tests/test_chore_template.py`; `uv run pytest` green (43 passed).

### Acceptance criteria

- [ ] A new `chores` app exists and is in `INSTALLED_APPS`.
- [ ] `ChoreTemplate` model: `title` (CharField), `description`
      (TextField, blank allowed), `default_point_value`
      (PositiveIntegerField, `MinValueValidator(1)`), `active`
      (BooleanField, `default=True`).
- [ ] Registered in the admin: list shows `title`,
      `default_point_value`, `active`; `active` is toggleable; create /
      edit / deactivate all work with no custom UI.
- [ ] `__str__` returns the title; `Meta.ordering` is deterministic
      (e.g. `["title"]`).
- [ ] Migration committed.
- [ ] Tests: a template is created, `active` defaults to `True`,
      `__str__` returns the title, `default_point_value=0` is rejected.

### Out of scope

- Spawning `Bounty` rows from templates — #16.
- The `Bounty` model — #7.
- Surge pricing (`plan.md` §5). Any non-admin UI.

### Constraints

- All code in `chores/`; admin-only management. No new dependencies.
- Deactivating a template must not touch `Bounty` rows already spawned
  from it (relevant once #7/#16 land).

### Dependencies

#1.

### Open decisions

- **Minimum point value.** Recommended: `>= 1` (a 0-point chore is
  meaningless). Change the validator if a 0 is genuinely wanted.

---

## 7. Bounty Model & State Machine

### Goal

Represent one chore instance on the board and its workflow states, with
model methods for each transition. This is the core state machine —
`architecture.md` §4 (fields), §5 (lifecycle), §8 (claim expiry);
`plan.md` §4.2–§4.3.

### Status

**Done.** `chores.Bounty` with all listed fields, distinct FK
`related_name`s, `status` `TextChoices` (OPEN/CLAIMED/PENDING_REVIEW/
APPROVED, default OPEN). `claim` / `submit` / `approve` / `reject` each
guard their source state (and `submit` the claimant), mutate only their
field set, and persist via `update_fields` — no caller `save()`. Invalid
transitions raise `chores.exceptions.InvalidTransition` (per the open
decision) and change nothing. `is_claim_expired` property; `__str__`;
`Meta.ordering = ["-created_at", "-id"]`. `CLAIM_WINDOW =
timedelta(hours=2)` module constant (for #12/#17). Migration
`0002_bounty`. Covered by `tests/test_bounty.py`; `uv run pytest` green
(62 passed).

### Acceptance criteria

- [ ] `Bounty` model in `chores` with: `title`, `description`,
      `point_value` (PositiveIntegerField), `status`, `claimed_by`
      (FK user, null/blank, `SET_NULL`), `claimed_at`,
      `claim_expires_at`, `submitted_at`, `reviewed_by` (FK user, null,
      distinct `related_name`), `reviewed_at`, `review_notes`
      (TextField, blank), `source_template` (FK `ChoreTemplate`, null,
      `SET_NULL`), `created_by` (FK user, null, `SET_NULL`).
- [ ] `status` is a `TextChoices` of `OPEN`, `CLAIMED`,
      `PENDING_REVIEW`, `APPROVED`; `default=OPEN`.
- [ ] Transition methods enforce the source state and mutate exactly the
      right fields:
      - `claim(user)` — from `OPEN` only; sets `claimed_by`,
        `claimed_at=now`, `claim_expires_at=now + CLAIM_WINDOW`, status
        `CLAIMED`.
      - `submit(user)` — from `CLAIMED` and only if `user == claimed_by`;
        sets `submitted_at=now`, status `PENDING_REVIEW`.
      - `approve(reviewer)` — from `PENDING_REVIEW` only; sets
        `reviewed_by`, `reviewed_at=now`, status `APPROVED`. Flips
        state only; the point award is #14 via #10's helper.
      - `reject(reviewer, notes="")` — from `PENDING_REVIEW` only; sets
        `reviewed_by`, `reviewed_at=now`, `review_notes`, status back to
        `CLAIMED`; leaves `claimed_by` / `claimed_at` /
        `claim_expires_at` untouched (do-over, no new timer —
        `architecture.md` §5).
- [ ] Every invalid transition (e.g. `submit()` on `OPEN`, `approve()` on
      `CLAIMED`, any transition out of `APPROVED`, `submit()` by a
      non-claimant) raises a clear exception and mutates nothing.
- [ ] `is_claim_expired` property: `status == CLAIMED and
      claim_expires_at is not None and claim_expires_at <= now`.
- [ ] `__str__`, deterministic `Meta.ordering`, migration committed.
- [ ] Tests (thorough, per `architecture.md` §13): each valid transition
      sets the exact field set + status; each invalid transition raises
      and leaves the row unchanged; `reject` preserves the claim fields;
      wrong-user `submit` rejected.

### Out of scope

- HTMX endpoints — #12 (claim), #13 (submit), #14 (approve/reject).
- Awarding points on approve — #10 + #14.
- Expiry sweep command and lazy revert — #17.
- Board view — #11. Ad-hoc creation form — #15. Surge pricing.

### Constraints

- All code in `chores/`. Use `django.utils.timezone.now` (`USE_TZ=True`
  already).
- `CLAIM_WINDOW = timedelta(hours=2)` as a named module constant, shared
  with #12 and #17 — do not inline `2` hours anywhere else.
- Transition methods persist their own change (wrap in
  `transaction.atomic` where more than one row is touched); document
  that callers don't need a separate `save()`.
- Reference the user model as `settings.AUTH_USER_MODEL`. Tests under
  `tests/`.

### Dependencies

#6 (for `source_template`). #1.

### Open decisions

- **Exception type for invalid transitions.** Recommended: a small
  custom `InvalidTransition(Exception)` in `chores`, so views (#12–#14)
  can map it to a 409 cleanly. `django.core.exceptions.ValidationError`
  is the alternative.

---

## 8. Perk Model

### Goal

Define items a user can redeem points for. Background:
`architecture.md` §3 (`store` app), §4.

### Acceptance criteria

- [ ] A new `store` app exists and is in `INSTALLED_APPS`.
- [ ] `Perk` model: `title`, `description` (blank allowed), `point_cost`
      (PositiveIntegerField, `MinValueValidator(1)`), `active`
      (BooleanField, `default=True`).
- [ ] Registered in the admin: list shows `title`, `point_cost`,
      `active`; create / edit / deactivate work with no custom UI.
- [ ] `__str__` returns the title; deterministic `Meta.ordering`.
- [ ] Migration committed.
- [ ] Tests: a perk is created, `active` defaults to `True`,
      `point_cost=0` is rejected.

### Out of scope

- The `Purchase` model and its workflow — #9.
- Store browsing / purchase UI — #18. Fulfilment — #19. Non-admin UI.

### Constraints

- All code in `store/`; admin-only management. No new dependencies.
- Deactivating a perk must not affect existing `Purchase` rows (relevant
  once #9 lands).

### Dependencies

#1.

---

## 9. Purchase Model & State Machine

### Goal

Represent one perk purchase and its fulfilment workflow. Background:
`architecture.md` §4, §5 (`LOCKED → FULFILLED`), §10.

### Acceptance criteria

- [ ] `Purchase` model in `store`: `perk` (FK `Perk`, `on_delete=PROTECT`
      — see decisions), `user` (FK user), `status` (`TextChoices`
      `LOCKED` / `FULFILLED`, `default=LOCKED`), `purchased_at`,
      `fulfilled_by` (FK user, null, distinct `related_name`),
      `fulfilled_at` (null).
- [ ] `fulfill(parent)` method: from `LOCKED` only; sets `fulfilled_by`,
      `fulfilled_at=now`, status `FULFILLED`. Called on an already
      `FULFILLED` row it raises and mutates nothing.
- [ ] `fulfill()` flips state only — the debit `PointTransaction` and
      balance update are #19 via #10's helper. This task does not touch
      points.
- [ ] `__str__`, `Meta.ordering` (e.g. `["-purchased_at"]`), migration
      committed.
- [ ] Tests: a new `Purchase` defaults to `LOCKED`; `fulfill()` sets the
      three fields + status; a second `fulfill()` raises.

### Out of scope

- Creating purchases + balance check — #18.
- The fulfilment queue view and the actual point debit — #19.
- The ledger — #10. The "available vs total balance" question
  (`architecture.md` §10, §14) — deferred.

### Constraints

- All code in `store/`. `timezone.now`; user as `settings.AUTH_USER_MODEL`.
  Tests under `tests/`.

### Dependencies

#8.

### Open decisions

- **`perk` FK `on_delete`.** Recommended: `PROTECT`, so a perk with
  purchase history can't be hard-deleted (deactivating is the intended
  path per #8). `SET_NULL` + nullable is the alternative if hard delete
  must stay possible.

---

## 10. Point Ledger Model

### Goal

Record every point award / spend as an immutable, auditable entry, and
keep a cheap cached balance that always equals the ledger sum.
Background: `architecture.md` §3 (`ledger` app), §4, §10.

### Acceptance criteria

- [ ] A new `ledger` app exists and is in `INSTALLED_APPS`.
- [ ] `PointTransaction` model: `user` (FK), `amount` (IntegerField,
      signed, non-zero), `reason` (CharField, `TextChoices`:
      `BOUNTY_AWARD`, `PERK_DEBIT`, `ADJUSTMENT`), `related_bounty` (FK
      `"chores.Bounty"`, null, `SET_NULL`), `related_purchase` (FK
      `"store.Purchase"`, null, `SET_NULL`), `created_at`
      (`auto_now_add`).
- [ ] Append-only: `save()` raises if called on a row that already
      exists; admin registration (if any) is fully read-only, no add /
      change / delete.
- [ ] `Profile.points_balance` is added here — `IntegerField(default=0)`
      — with its migration (per the #4 grooming decision).
- [ ] A helper `record_transaction(user, amount, reason, *,
      related_bounty=None, related_purchase=None)` inserts the row and
      updates `Profile.points_balance` with an `F()` expression inside
      one `transaction.atomic()`, and returns the transaction.
- [ ] `amount == 0` is rejected by the helper.
- [ ] Invariant test: after a mixed series of `record_transaction` calls
      (credits and debits), `profile.points_balance == sum(that user's
      PointTransaction.amount)`.
- [ ] Migrations committed.

### Out of scope

- Call sites — awarding on approve (#14), debiting on fulfil (#19).
- "Available vs total" balance display (`architecture.md` §10, §14) —
  deferred. The balance header partial — #20.

### Constraints

- All new code in `ledger/` plus the one-field migration on
  `accounts.Profile`. Cross-app FKs as string references to avoid import
  cycles. `record_transaction` is the only supported write path for
  points. `F()` + `transaction.atomic` throughout. Tests under `tests/`.

### Dependencies

#4 (`Profile`), #7 (`Bounty`), #9 (`Purchase`).

---

## 11. Read-Only Bounty Board View

### Goal

Any logged-in user can see the current list of bounties that aren't yet
approved (open, claimed, pending review), display-only. Background:
`architecture.md` §7.

### Acceptance criteria

- [ ] A `@login_required` view at a stable URL renders every `Bounty`
      with `status != APPROVED`, showing title, point value, status, and
      claimant (when set).
- [ ] Anonymous request → redirect to login.
- [ ] An empty board renders a friendly empty state, no error.
- [ ] Ordering is deterministic (e.g. `OPEN` first, then by
      `point_value` desc).
- [ ] Each bounty renders through a row/card partial with a stable DOM
      id (e.g. `id="bounty-{{ bounty.pk }}"`) so #12–#14 can target it —
      but this task adds no action buttons, forms, or HTMX.
- [ ] Tests: anonymous → redirect; authed → 200; an `OPEN` and a
      `CLAIMED` bounty both appear (claimant name shown for the claimed
      one); an `APPROVED` bounty does not appear.

### Out of scope

- Claim (#12), submit (#13), review (#14) actions.
- Lazy expiry revert — added into this view by #17.
- Perk store (#18), points header (#20), visual design
  (`_docs/design-system.md` is empty).

### Constraints

- View + templates in `dashboard/`; the row partial is the one #12–#14
  will re-render. No model changes. Tests under `tests/`.

### Dependencies

#7 (`Bounty`), #3 (login).

---

## 12. Claim Action (HTMX)

### Goal

Let a child claim an open bounty from the board, returning the updated
row as an HTML fragment. Background: `architecture.md` §7, §8;
`plan.md` §4.2 (two-hour window).

### Acceptance criteria

- [ ] A POST endpoint (e.g. `/board/<pk>/claim/`), `@login_required`,
      calls `Bounty.claim(request.user)` — `OPEN → CLAIMED`, setting
      `claimed_by`, `claimed_at`, `claim_expires_at = now + CLAIM_WINDOW`
      (the #7 constant).
- [ ] Success returns only the updated bounty row partial, not a full
      page.
- [ ] Rejected, with a fragment / message and an appropriate status:
      requester is not a child (403); bounty is not currently `OPEN`
      (409); bounty missing (404).
- [ ] `GET` on the endpoint → 405. CSRF is enforced (document the
      base-template HTMX token setup).
- [ ] Two concurrent claims on the same `OPEN` bounty → exactly one wins
      (`select_for_update`, or a conditional `UPDATE … WHERE
      status='OPEN'`).
- [ ] Tests: child claims `OPEN` → `CLAIMED` + fields set + fragment
      returned; parent → 403; claim on already-`CLAIMED` → 409;
      anonymous → login redirect; `GET` → 405.

### Out of scope

- Submit (#13); the cosmetic claim-countdown timer (`architecture.md`
  §7); expiry revert (#17); the board list itself (#11).

### Constraints

- Endpoint + partial in `dashboard/`; reuse the #11 row partial and the
  `Bounty.claim` method — no re-implemented transition logic. Child-only
  check via #5's helper (or an inline `role == CHILD`). Tests under
  `tests/`.

### Dependencies

#7, #11, #4 (role). #5 if the child check lives there.

---

## 13. Submit Action (HTMX)

### Goal

Let a child mark their claimed chore done and ready for review,
returning the updated row fragment. Background: `architecture.md` §5,
§7.

### Acceptance criteria

- [ ] A POST endpoint (e.g. `/board/<pk>/submit/`), `@login_required`,
      calls `Bounty.submit(request.user)` — `CLAIMED → PENDING_REVIEW`,
      setting `submitted_at` — only when `request.user == claimed_by` and
      status is `CLAIMED`.
- [ ] Success returns the updated row partial.
- [ ] Rejected: bounty not claimed by this user (403); not in `CLAIMED`
      state (409); missing (404); `GET` (405).
- [ ] A claim whose window has already passed but hasn't been swept:
      `submit()` fails, and the row is reverted to `OPEN` inline (shared
      revert helper from #17).
- [ ] Tests: happy path; another user's bounty → rejected; `submit` on
      `OPEN` → rejected; `submit` twice → second rejected; anonymous →
      redirect; expired claim → reverted + rejected.

### Out of scope

- Review / approve / reject (#14); the expiry sweep command (#17);
  points.

### Constraints

- As #12 — `dashboard/`, reuse the row partial and `Bounty.submit`.
  Tests under `tests/`.

### Dependencies

#7, #11, #12 (logical order), #4.

---

## 14. Parent Review Queue & Approve/Reject Actions (HTMX)

### Goal

Let a parent approve or reject a submitted chore; approving awards the
point value to the claimant. Background: `architecture.md` §5, §7, §10.

### Acceptance criteria

- [ ] A `parent_required` (#5) view lists every `PENDING_REVIEW` bounty
      with title, claimant, point value, `submitted_at`.
- [ ] Approve POST: `Bounty.approve(request.user)` → `APPROVED`, and in
      the same `transaction.atomic()` awards points via
      `record_transaction(claimed_by, +point_value, BOUNTY_AWARD,
      related_bounty=bounty)` (#10). Returns the updated fragment.
- [ ] Reject POST: `Bounty.reject(request.user, notes=<optional POST
      field>)` → back to `CLAIMED`, claim fields untouched, no new
      timer, no ledger row. Returns the updated fragment.
- [ ] A child hitting either endpoint → 403.
- [ ] Approve or reject on a bounty not in `PENDING_REVIEW` → 409;
      a double-submitted approve awards points exactly once (state check
      inside the atomic block).
- [ ] `GET` on the action endpoints → 405.
- [ ] Tests: parent approve → `APPROVED` + exactly one ledger row +
      balance up by `point_value`; parent reject → `CLAIMED` + no ledger
      row + claim fields intact; child → 403; approve-again → 409, still
      one ledger row; queue lists only `PENDING_REVIEW`.

### Out of scope

- The balance header partial itself — #20 (this task may include the
  OOB balance snippet in its response, or #20 retrofits it).
- Ad-hoc creation (#15); fulfilment (#19).

### Constraints

- `dashboard/`; `parent_required`; `record_transaction` is the only way
  points move; one atomic block per action. Tests under `tests/`.

### Dependencies

#7, #10, #5.

---

## 15. Ad-Hoc Bounty Creation Form

### Goal

Let a parent post a one-off chore outside the weekly template cycle.
Background: `plan.md` §4.1; `architecture.md` §4 (`created_by`,
`source_template` null for ad-hoc).

### Acceptance criteria

- [ ] A `parent_required` view with a `ModelForm` over `title`,
      `description`, `point_value`.
- [ ] `GET` renders the form.
- [ ] Valid POST → creates a `Bounty` with status `OPEN`,
      `created_by=request.user`, `source_template=None`; then redirects
      (to the board).
- [ ] Invalid POST (blank title, `point_value < 1`) → form re-rendered
      with errors, no `Bounty` created.
- [ ] A child `GET` or POST → 403 and no `Bounty` created (explicit test,
      per the task text). Anonymous → login redirect.
- [ ] Tests: parent `GET` 200; parent valid POST → `OPEN` bounty with
      `created_by` set; parent invalid POST → no create + errors; child
      POST → 403 + no create.

### Out of scope

- Weekly template spawning (#16); surge pricing (`plan.md` §5);
  editing / deleting bounties; HTMX (a plain form + redirect is fine —
  the task asks for a form, not a fragment).

### Constraints

- `dashboard/`; `parent_required`; `ModelForm` with a `point_value`
  `MinValueValidator(1)`. Tests under `tests/`.

### Dependencies

#7, #5.

---

## 16. Weekly Reset Management Command

### Goal

Automatically repopulate the board from active chore templates, intended
to run weekly via cron. Background: `architecture.md` §8.

### Acceptance criteria

- [ ] `chores/management/commands/reset_weekly_board.py` (a
      `BaseCommand`).
- [ ] Running it creates one `Bounty` per `ChoreTemplate` with
      `active=True`: status `OPEN`, `title` / `description` copied,
      `point_value = template.default_point_value`,
      `source_template=<that template>`, `created_by=None`.
- [ ] Inactive templates are skipped.
- [ ] The command's `help` / docstring states the intended schedule
      (e.g. "run weekly, Sunday 00:00 local, via cron").
- [ ] It prints/logs how many bounties it created, and runs inside one
      `transaction.atomic()`.
- [ ] Running it twice does not skip active templates and does not error
      (see decisions for duplicate semantics); with no active templates
      it creates nothing and exits cleanly.
- [ ] Tests: 2 active + 1 inactive template → 2 `OPEN` bounties linked to
      the right templates; second run behaves per the chosen semantics;
      the inactive template never spawns.

### Out of scope

- Installing the cron entry; the Phase 2 batched Discord notification
  (`architecture.md` §8, §9); the expiry sweep (#17); surge pricing.

### Constraints

- `chores` management command; `transaction.atomic`; no new
  dependencies. Tests use `call_command`.

### Dependencies

#6, #7.

### Open decisions

- **Repeat-run semantics.** Recommended: each run spawns one bounty per
  active template unconditionally; cron runs it once a week, so
  duplicates don't arise in practice, and the docstring says so.
  Alternative: skip a template that already has an `OPEN` bounty created
  within the last N days (more code, not asked for).

---

## 17. Claim-Expiry Sweep (Command + Lazy Check)

### Goal

Return unfinished claimed chores to the board once the claim window has
passed — both via a cron command and lazily when the board is viewed.
Background: `architecture.md` §8, §14.

### Acceptance criteria

- [ ] `chores/management/commands/sweep_expired_claims.py`: finds every
      `Bounty` with `status=CLAIMED` and `claim_expires_at <= now`,
      resets it to `OPEN`, and clears `claimed_by` / `claimed_at` /
      `claim_expires_at`. No rejection, no penalty.
- [ ] The revert logic lives in one shared place (a manager method /
      `QuerySet` method, e.g. `Bounty.objects.release_expired()`), used
      by both the command and the board view.
- [ ] The board view (#11) reverts any expired claimed bounty inline
      before rendering, so it shows as `OPEN` even between cron runs.
- [ ] A `PENDING_REVIEW` bounty with a past `claim_expires_at` is left
      alone (already submitted).
- [ ] Boundary: `claim_expires_at == now` counts as expired (`<= now`).
- [ ] The command is a safe no-op when nothing is expired and on repeated
      runs.
- [ ] The command's docstring states the intended cadence (~5 min via
      cron — `architecture.md` §14 open question, proposed 5 min).
- [ ] Tests both paths: (a) the command reverts an expired `CLAIMED`
      bounty and leaves a fresh `CLAIMED` one and a `PENDING_REVIEW` one
      untouched; (b) a `client.get` of the board reverts an expired claim
      and renders it as `OPEN`; (c) the command is a clean no-op when
      nothing is expired.

### Out of scope

- The cosmetic countdown timer; the Phase 2 "returned to board" webhook
  (`architecture.md` §8, §9); the weekly reset (#16).

### Constraints

- One shared revert implementation — no copy/paste between command and
  view. `timezone.now`; `transaction.atomic`. Tests under `tests/` using
  `call_command` and the test client.

### Dependencies

#7, #11.

---

## 18. Perk Store Browsing & Purchase Action (HTMX)

### Goal

Let a user browse active perks and spend points to buy one, creating a
locked purchase. Background: `architecture.md` §5, §10, §14.

### Acceptance criteria

- [ ] A `@login_required` view lists `Perk` rows with `active=True`
      (title, description, point cost) alongside the signed-in user's
      `profile.points_balance`.
- [ ] An HTMX purchase POST (e.g. `/store/<pk>/buy/`): when
      `profile.points_balance >= perk.point_cost`, creates
      `Purchase(user=request.user, perk=perk, status=LOCKED,
      purchased_at=now)` and returns the updated fragment.
- [ ] Insufficient balance → no `Purchase` created, fragment returned
      with a clear message.
- [ ] Inactive or missing perk → 404 / rejected; `GET` → 405; anonymous
      → login redirect.
- [ ] Two concurrent purchases when the balance covers only one → at
      most one succeeds (`select_for_update` on the profile, or an
      atomic conditional check).
- [ ] Tests: enough points → `LOCKED` `Purchase` created + fragment;
      not enough → no `Purchase` + error message; inactive perk not
      listed; anonymous → redirect.

### Out of scope

- Fulfilment and the actual point debit — #19.
- The balance header partial — #20.
- Cancelling / refunding a purchase.

### Constraints

- View + templates in `dashboard/` (consistent with #11/#14). No ledger
  write here — `points_balance` is not changed until fulfilment (#19).
  Tests under `tests/`.

### Dependencies

#8, #9, #10 (`points_balance` field), #4.

### Open decisions

- **Does `LOCKED` reduce the shown balance?** `architecture.md` §10/§14
  open question. Recommended for v1: no — `points_balance` is unchanged
  at purchase and only debited at fulfilment (#19); optionally show a
  separate "N points locked in pending purchases" figure. The balance
  check above is against the full `points_balance`.

---

## 19. Parent Fulfilment Queue & Fulfill Action (HTMX)

### Goal

Let a parent mark a purchased perk as delivered and finalise the point
spend. Background: `architecture.md` §5, §10.

### Acceptance criteria

- [ ] A `parent_required` view lists every `Purchase` with
      `status=LOCKED` (buyer, perk, point cost, `purchased_at`).
- [ ] Fulfill POST: `Purchase.fulfill(request.user)` → `FULFILLED` +
      `fulfilled_by` / `fulfilled_at`, and in the same
      `transaction.atomic()` records the debit via
      `record_transaction(purchase.user, -perk.point_cost, PERK_DEBIT,
      related_purchase=purchase)` (#10). Returns the updated fragment.
- [ ] A child hitting the endpoint → 403 and nothing changes (explicit
      test, per the task text).
- [ ] Fulfill on an already `FULFILLED` purchase → rejected, no second
      debit (state check inside the atomic block).
- [ ] `GET` → 405; anonymous → login redirect.
- [ ] Tests: parent fulfils → `FULFILLED` + exactly one debit ledger row
      + balance down by `point_cost`; child → 403 + no change; fulfil
      twice → second rejected, still one debit; queue lists only
      `LOCKED`.

### Out of scope

- The reservation / "available balance" model (`architecture.md` §14) —
  deferred. The balance header partial — #20. Purchase creation — #18.

### Constraints

- `dashboard/`; `parent_required`; `record_transaction` for the debit;
  one atomic block per action. Tests under `tests/`.

### Dependencies

#9, #10, #5, #18.

### Open decisions

- **Balance can go negative** if points were spent elsewhere between
  purchase and fulfilment (v1 doesn't reserve at `LOCKED`). Recommended:
  allow it — the parent has already handed over the reward — and accept
  this as the known cost of the deferred §14 decision.

---

## 20. Points Balance Header Component

### Goal

Show the signed-in user's point balance on every page and keep it live
via HTMX out-of-band swaps after any action that changes it. Background:
`architecture.md` §7, §10.

### Acceptance criteria

- [ ] A template partial (e.g. `dashboard/templates/dashboard/
      _balance.html`) renders `points_balance` inside an element with a
      stable id (e.g. `id="points-balance"`) and an
      `hx-swap-oob="true"` variant for action responses.
- [ ] The base template header includes it for authenticated users;
      anonymous pages have no balance element.
- [ ] A small context processor (in `accounts`) supplies the balance to
      all templates, so normal full-page loads render the current
      number.
- [ ] The point-changing action responses — approve (#14), purchase
      (#18), fulfill (#19) — include the OOB partial so the header
      updates with no full-page reload.
- [ ] Tests: an authed page contains the balance element with the right
      number; after an approve / purchase / fulfil HTMX POST, the
      response body contains the OOB partial with the updated number;
      an anonymous page has no balance element.

### Out of scope

- "Available vs total" split (`architecture.md` §14) — deferred.
- Any other header content (nav, etc.) beyond the minimum.
- Visual design (`_docs/design-system.md` is empty).

### Constraints

- Touches the `dashboard` base template, an `accounts` context
  processor, and the three action views (#14/#18/#19) to add the OOB
  partial. Keep the partial tiny. Tests under `tests/`.

### Dependencies

#10, #14, #18, #19, and a real `base.html` (started in #3/#11).

---

## 21. Dev Seed Data

### Goal

Make the app usable out of the box: one command populates a demo board,
perks, and a parent + child account. Background: task list intro (local
dev / demo).

### Acceptance criteria

- [ ] A management command (e.g. `chores/management/commands/
      seed_dev.py`) creates: a few `ChoreTemplate` rows, a few `Perk`
      rows, one parent `User` (`Profile.role = PARENT`) and one child
      `User` (default child profile).
- [ ] It prints the seeded usernames and passwords.
- [ ] It is safe to run more than once — `get_or_create` keyed on
      natural fields, no duplicate pile-up, no unique-constraint crash.
- [ ] It refuses to run (or warns loudly) when `DEBUG` is `False`.
- [ ] It does not write `PointTransaction` rows / balances directly
      (leave balances at 0); if it ever needs to, it goes through
      `record_transaction` (#10).
- [ ] It leaves the board populated — either by calling
      `reset_weekly_board` (#16) after creating templates, or by
      creating a couple of `OPEN` bounties directly.
- [ ] The README gains a short section: how to run it, the seeded
      credentials, and that it's dev-only.
- [ ] Tests: running the command creates the expected counts; a second
      run doesn't duplicate; the parent has role `PARENT`, the child
      `CHILD`.

### Out of scope

- Production / staging seeding; test factories (tests build their own
  objects); CI wiring.

### Constraints

- A management command (not a raw fixture, so the `DEBUG` guard and
  `get_or_create` logic have a home); `get_or_create` throughout;
  README updated; no new dependencies. Tests via `call_command`.

### Dependencies

#4, #6, #7, #8, #10; #16 if it calls `reset_weekly_board`.
