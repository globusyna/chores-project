# Household Chore Bounty Board - Architecture

Companion to `plan.md`. Describes how the confirmed stack (Django + HTMX +
SQLite) implements the features in the plan. No code yet — this is the
shape the code will follow.

## 1. Overview

A single Django monolith, server-rendered, with HTMX handling partial-page
updates so claiming/approving/rejecting/fulfilling feel app-like without a
separate frontend build. One process, one SQLite file, run on a home
server / small VM at family scale — no microservices, no queue broker.

```
Browser (HTMX) <--> Django views <--> SQLite
                          |
                          +--> Username/password auth (Django built-in)
                          +--> Cron-triggered management commands
                                 (weekly reset, claim-expiry sweep)
                          |
                          +--> [Phase 2] Discord OAuth (login)
                          +--> [Phase 2] Discord Webhooks (outbound)
```

**V1 scope:** authentication is Django's built-in username/password auth
and there are no outbound Discord notifications — both are deferred,
marked `[Phase 2]` above. See §6 and §9.

## 2. Tech Stack

| Concern | Choice |
|---|---|
| Backend framework | Django |
| Dynamic UI | HTMX (server-rendered partials, no SPA) |
| Database | SQLite |
| Auth | Username/password, Django's built-in auth (v1) — Discord OAuth via `django-allauth` deferred to Phase 2 (§6) |
| Outbound notifications | None in v1 — Discord Incoming Webhooks deferred to Phase 2 (§9) |
| Scheduled jobs | Management commands run via system cron (no Celery/Redis for MVP) |
| Styling | Server-rendered templates + minimal CSS (framework TBD, not architecturally significant) |

## 3. Application Structure

Django apps, split by domain rather than by layer:

- **`accounts`** — extends the Discord-authenticated `User` with a
  `Profile` (role: Parent/Child, cached points balance). Owns role-based
  permission helpers (`@parent_required`, queryset scoping for children).
- **`chores`** — the bounty board: `ChoreTemplate`, `Bounty`, the
  claim/submit/approve/reject workflow, and the weekly-reset and
  claim-expiry management commands.
- **`store`** — the Perk Store: `Perk`, `Purchase`, and the
  purchase/fulfillment workflow.
- **`ledger`** — `PointTransaction`, the shared point-economy primitive
  used by both `chores` (awarding points) and `store` (spending them).
- **`notifications`** — *(Phase 2, not built in v1)* thin Discord
  webhook client plus the explicit call sites that fire it on key
  events. Nothing in v1 depends on this app existing.
- **`dashboard`** — the views and templates that compose the above into
  the actual pages (bounty board, perk store, parent review queue), plus
  the HTMX partial-view endpoints.

Each domain app owns its own models and business logic; `dashboard` is
presentation-only and depends on the others, not vice versa.

## 4. Data Model

**Core entities:**

- **Profile** — one-to-one with Django `User`. `discord_id`, `role`
  (`PARENT` / `CHILD`), `points_balance` (denormalized cache, see
  §10).
- **ChoreTemplate** — the recurring-chore definition used to repopulate
  the board each week. `title`, `description`, `default_point_value`,
  `active`.
- **Bounty** — one instance of a chore on the board (either spawned from
  a `ChoreTemplate` or created ad hoc by a parent). `title`,
  `description`, `point_value`, `status`, `claimed_by` (FK to `User`,
  nullable), `claimed_at`, `claim_expires_at`, `submitted_at`,
  `reviewed_by`, `reviewed_at`, `review_notes`, `source_template` (FK,
  nullable), `created_by`.
- **Perk** — a purchasable reward. `title`, `description`, `point_cost`,
  `active`.
- **Purchase** — one perk purchase. `perk` (FK), `user` (FK), `status`,
  `purchased_at`, `fulfilled_by`, `fulfilled_at`.
- **PointTransaction** — append-only ledger row. `user` (FK), `amount`
  (signed), `reason`, `related_bounty` (FK, nullable),
  `related_purchase` (FK, nullable), `created_at`.

**Relationships:** `User` 1—1 `Profile`; `User` 1—N `Bounty` (as
claimant), 1—N `Purchase`, 1—N `PointTransaction`; `ChoreTemplate` 1—N
`Bounty`; `Perk` 1—N `Purchase`.

`Bounty` and `Purchase` deliberately stay single tables with a `status`
field rather than being split into separate "claim"/"submission" tables —
the plan's workflow is a linear state machine per bounty, and Django's
`status` + timestamp columns capture it without extra joins. `Purchase`
is separate from `PointTransaction` because a purchase is a workflow
object (locked → fulfilled) while a transaction is an immutable ledger
entry; a purchase produces exactly one debit transaction when fulfilled.

## 5. State Machines

**Bounty lifecycle:**

```
OPEN --(claim)--> CLAIMED --(submit)--> PENDING_REVIEW
                     ^                        |
                     |                  (parent rejects)
                     +------------------------+
                                              |
                                        (parent approves)
                                              v
                                          APPROVED  [points awarded, terminal]
```

- `CLAIMED -> OPEN` also happens automatically when `claim_expires_at`
  passes without a submission (see §8) — `claimed_by`/`claimed_at` are
  cleared, no rejection penalty.
- `PENDING_REVIEW -> CLAIMED` on rejection ("Do Over" protocol): stays
  locked to the same user, no new claim window/timer, just resubmit.
- `APPROVED` is terminal for that `Bounty` instance and is when the
  `PointTransaction` credit is created.

**Purchase lifecycle:**

```
LOCKED --(parent fulfills)--> FULFILLED  [debit transaction created, terminal]
```

- Points are provisionally reserved at `LOCKED` (reflected in an
  "available" balance if we choose to show one — see §10 open question)
  and permanently deducted only at `FULFILLED`, matching the plan's
  "temporarily locked... permanently deducted before Fulfill" language.

## 6. Authentication & Authorization

- **V1:** login is Django's built-in username/password auth
  (`django.contrib.auth`) — no OAuth, no external dependency. Accounts
  are created by a parent (Django admin, or a simple creation flow)
  rather than self-service signup, since this is a closed family app.
- **Phase 2 (deferred):** swap in Discord OAuth via `django-allauth`'s
  Discord provider. Because `Profile.role` lives on a model separate
  from the auth mechanism itself, this is intended to be a swap of the
  login method, not a rework of the permission model — existing
  accounts would need a one-time linking step to a Discord identity,
  a decision to make when that phase starts, not now.
- First-account role assignment (either phase): a new `Profile` defaults
  to `CHILD`; a parent is promoted manually (Django admin, or a
  one-time management-command bootstrap for the first parent account).
- Authorization is role-based, not per-object ACLs — two roles, enforced
  at the view layer via a `parent_required` decorator/mixin and by
  scoping child-facing querysets to actions they're allowed to take
  (claim, submit, purchase) versus parent-only actions (create ad-hoc
  bounty, approve/reject, fulfill). This layer is unaffected by which
  phase's login mechanism is active.
- Django's built-in admin is available to parents as a break-glass tool
  for data fixes, gated by `is_staff`/role — not the primary UI.

## 7. Frontend / HTMX Interaction Pattern

- Full pages are server-rendered Django templates.
- Stateful actions (claim, submit, approve, reject, purchase, fulfill)
  are HTMX-triggered POSTs (`hx-post`) against small, action-specific
  views that mutate one `Bounty`/`Purchase` and return an updated HTML
  fragment for that row/card (`hx-target` + `hx-swap`), not a full page
  reload.
- The points-balance display updates via an HTMX out-of-band swap
  (`hx-swap-oob`) piggybacked on the same response, so an action that
  changes points refreshes the balance in the header without a separate
  request.
- No client-side state store — HTMX + server-rendered fragments is the
  entire frontend architecture; the only JS is what HTMX itself needs,
  plus perhaps a small script for the claim-timer countdown display
  (cosmetic only — the real expiry check is always server-side, see
  §8).

## 8. Background Jobs & Scheduling

No Celery/Redis for the MVP — two Django management commands, invoked by
system cron:

- **`reset_weekly_board`** — runs weekly (e.g., Sunday midnight): for
  each active `ChoreTemplate`, spawns a new `Bounty` in `OPEN` status.
  *(Phase 2: also fires a batched Discord notification here — no-op in
  v1.)*
- **`sweep_expired_claims`** — runs frequently (e.g., every 5 minutes):
  finds `Bounty` rows in `CLAIMED` with `claim_expires_at` in the past,
  resets them to `OPEN`, clears claim fields.

Because cron granularity alone could leave a stale claim visible for a
few minutes, expiry is **also checked lazily**: any view that reads a
`CLAIMED` bounty (e.g., rendering the board) re-checks
`claim_expires_at` and reverts it inline before rendering if it has
passed. The cron sweep exists for hygiene (so it reverts even if nobody
loads the board) and — once Phase 2 lands — will be the single place
that fires the "chore returned to board" webhook; the lazy check exists
for correctness between sweeps regardless of phase.

## 9. Discord Integration — Deferred to Phase 2

Out of scope for the first implementation. Documented here so the
design is ready when it's picked up, not because v1 depends on it.

- **Auth:** OAuth2 login handled entirely by `django-allauth`'s Discord
  provider — no custom OAuth code. Replaces the v1 username/password
  login (§6).
- **Notifications:** outbound only, via a single family Discord
  webhook URL (Django setting / env var). A small `notifications`
  service wraps the HTTP POST; call sites are explicit (from the
  view/command that performs the action) rather than Django signals, to
  keep "what triggers a notification" easy to grep for.
- **Events notified (per plan §4.5):** ad-hoc bounty posted, chore
  submitted for review, chore approved/rejected, perk purchased,
  perk fulfilled. Weekly reset and expiry sweeps notify in a batched/
  summarized form rather than one message per chore, to avoid channel
  spam.
- Webhook failures are logged and swallowed, not surfaced to the user —
  Discord notification is a nice-to-have, never a blocker for the
  underlying action succeeding.

## 10. Point Economy & Ledger

- `PointTransaction` is the source of truth (append-only, one row per
  award/spend); `Profile.points_balance` is a denormalized cache updated
  in the same DB transaction as each `PointTransaction` insert, so reads
  (displaying the balance) stay cheap and correct.
- Award happens at `Bounty.APPROVED`; debit happens at
  `Purchase.FULFILLED`.
- **Open question (deferred to implementation):** whether "locked"
  purchase points should be excluded from the displayed balance
  immediately at `LOCKED` (showing an "available" vs "total" balance) or
  only deducted at `FULFILLED` with no interim visual change. The plan's
  wording ("temporarily locked... permanently deducted") suggests the
  former is the more faithful reading; flagging it here rather than
  deciding silently in code.

## 11. Security Considerations

- CSRF protection via Django's built-in middleware applies to all HTMX
  POSTs (HTMX sends the CSRF token header automatically once configured
  from the page's cookie/meta tag).
- Role checks happen server-side on every state-changing view — HTMX
  swapping out a button in the DOM is not itself an authorization
  boundary; a child hitting a parent-only endpoint directly must be
  rejected server-side regardless of what the UI shows them.
- V1 passwords rely on Django's default password hashing
  (PBKDF2/Argon2 depending on config) — no custom crypto, no passwords
  stored or logged in plaintext.
- *(Phase 2)* Discord webhook URL will be a secret (treat like an API
  key — env var, not committed) since anyone holding it can post into
  the family channel.
- SQLite file and any `.env`/secrets (including `SECRET_KEY` and, later,
  the webhook URL) belong in `.gitignore` (not yet present in this
  repo — noted as a to-do, see §14).

## 12. Deployment

- Single process (`gunicorn` or Django's dev server behind a reverse
  proxy for real use), single SQLite file on disk, cron entries for the
  two management commands from §8.
- No containerization/orchestration required at this scale, though a
  simple Dockerfile is a reasonable later convenience, not an
  architectural dependency.
- Out of scope per the plan: migrating to Postgres, horizontal scaling,
  multi-tenancy (this is a single-family app).

## 13. Testing Strategy

- Django's `TestCase` (or `pytest-django`) for model/state-machine unit
  tests — especially the `Bounty` and `Purchase` transitions and the
  claim-expiry logic, since those are the parts most likely to have
  off-by-one/timing bugs.
- View-level tests for permission boundaries (child cannot hit
  parent-only endpoints) and for the HTMX fragment endpoints returning
  the expected partial + correct status codes.
- Discord webhook calls mocked/stubbed in tests — never hit the real
  webhook from the test suite.

## 14. Open Questions / Decisions Deferred

- Available-vs-total balance display during a `LOCKED` purchase (§10).
- Exact cron cadence for `sweep_expired_claims` (proposed: 5 minutes).
- Whether the first parent account is bootstrapped via a management
  command, a fixture, or manually through `/admin`.
- `.gitignore` / secrets handling isn't set up yet in this repo — needed
  before `SECRET_KEY` lands in the working tree, and later the Discord
  webhook URL once Phase 2 starts.
- How existing username/password accounts get linked to a Discord
  identity when Phase 2 (Discord OAuth) is picked up — resolved at that
  time, not now.
