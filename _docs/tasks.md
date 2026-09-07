# Household Chore Bounty Board - Backlog (V1)

Companion to `plan.md` and `architecture.md`. Scope is the v1 slice
only: Django + HTMX + SQLite, username/password auth, no Discord
integration (deferred to Phase 2 per `architecture.md` §6/§9 — those
tasks aren't listed here and will get their own backlog later).

Each task below is meant to be understandable and completable on its
own, without reading the others — cross-references point to
`plan.md`/`architecture.md` sections rather than to other task numbers.
Numbering reflects a sensible build order, not a hard dependency chain.

## 1. Project Scaffolding & First Passing Test
Goal: Stand up an empty, runnable Django project with one test that passes.
Description: Create the Django project and a minimal app inside it, wired into `INSTALLED_APPS`, pointing at a SQLite database with default settings. Add one trivial test (e.g., a homepage view returning HTTP 200) and confirm `manage.py test` runs green. No models, auth, or business logic yet — this task only proves the toolchain works end to end.

## 2. Secrets & .gitignore Setup
Goal: Keep credentials and local artifacts out of version control.
Description: Add a `.gitignore` covering the SQLite database file, `__pycache__`, virtualenv directories, and any `.env` file. Move `SECRET_KEY` (and any other sensitive setting) out of `settings.py` into an environment variable read at startup, with a `.env.example` showing the expected variable names but no real values.

## 3. Username/Password Authentication
Goal: Let a user log in and out with a username and password.
Description: Wire up Django's built-in `django.contrib.auth` login/logout views plus a minimal login template. There's no self-service signup for this app — accounts are created by a parent, not registered by users — so this task covers only signing in/out with an existing account.

## 4. Profile Model & Roles
Goal: Track whether a logged-in user is a Parent or a Child.
Description: Add a `Profile` model, one-to-one with Django's `User`, with a `role` field (`PARENT` or `CHILD`); new profiles default to `CHILD`. Register `Profile` in the Django admin so a parent can promote an account to `PARENT` by hand for now, with no custom UI needed yet.

## 5. Parent-Only Access Control Helper
Goal: A reusable way to restrict a view to parent accounts only.
Description: Add a `parent_required` decorator (or class-based mixin) that checks the signed-in user's role and returns a 403/redirect for non-parents. Cover it with a test that hits a dummy parent-only view as both a parent and a child account and asserts the expected outcome for each.

## 6. Chore Template Model
Goal: Define the recurring chores that repopulate the board each week.
Description: Add a `ChoreTemplate` model with `title`, `description`, `default_point_value`, and `active` fields. Register it in the Django admin so a parent can create, edit, and deactivate templates without any custom UI.

## 7. Bounty Model & State Machine
Goal: Represent one chore instance on the board and its workflow states.
Description: Add a `Bounty` model with `title`, `description`, `point_value`, `status`, `claimed_by`, `claimed_at`, `claim_expires_at`, `submitted_at`, `reviewed_by`, `reviewed_at`, `review_notes`, and `created_by` fields. Status cycles `OPEN → CLAIMED → PENDING_REVIEW → APPROVED`, with `PENDING_REVIEW → CLAIMED` on rejection; add model methods for each transition (`claim()`, `submit()`, `approve()`, `reject()`) and tests confirming valid transitions update the right fields and invalid ones (e.g., submitting an `OPEN` bounty) are rejected.

## 8. Perk Model
Goal: Define items a user can redeem points for.
Description: Add a `Perk` model with `title`, `description`, `point_cost`, and `active` fields. Register it in the Django admin so a parent can create, edit, and deactivate perks.

## 9. Purchase Model & State Machine
Goal: Represent one perk purchase and its fulfillment workflow.
Description: Add a `Purchase` model linking a perk and a user, with `status`, `purchased_at`, `fulfilled_by`, and `fulfilled_at` fields, moving `LOCKED → FULFILLED`. Add a `fulfill()` model method and a test confirming it sets the fulfillment fields and flips the status.

## 10. Point Ledger Model
Goal: Record every point award/spend as an immutable, auditable entry.
Description: Add a `PointTransaction` model with `user`, signed `amount`, `reason`, optional links to the related bounty or purchase, and `created_at`. Add a helper function that writes a transaction and updates the user's cached points balance in the same database transaction, with a test confirming the cached balance always equals the sum of that user's ledger entries.

## 11. Read-Only Bounty Board View
Goal: Let any logged-in user see the current list of open and claimed bounties.
Description: Add a view and template listing all bounties that aren't yet approved, showing title, point value, status, and claimant (if any). This task is display-only — no claim, submit, or review actions belong here; those are separate tasks.

## 12. Claim Action (HTMX)
Goal: Let a child claim an open bounty from the board.
Description: Add an HTMX-powered endpoint that, on request from a signed-in child, moves one open bounty to claimed, records who claimed it and when, and sets a two-hour expiry timer on the claim, returning the updated row as an HTML fragment. Reject the request if the bounty isn't currently open or the requester isn't a child.

## 13. Submit Action (HTMX)
Goal: Let a child mark their claimed chore as done and ready for review.
Description: Add an HTMX-powered endpoint that moves a bounty the requesting user has claimed from claimed to pending-review and records the submission time, returning the updated row fragment. Reject the request if the bounty isn't claimed by that user or isn't currently in the claimed state.

## 14. Parent Review Queue & Approve/Reject Actions (HTMX)
Goal: Let a parent approve or reject a submitted chore.
Description: Add a parent-only view listing all pending-review bounties, with an Approve action that marks the bounty approved and awards its point value to the claimant, and a Reject action that sends it back to claimed (the household's "redo" workflow) without touching points. Both actions are HTMX requests that return the updated fragment.

## 15. Ad-Hoc Bounty Creation Form
Goal: Let a parent post a one-off chore outside the weekly template cycle.
Description: Add a parent-only form and view for creating a bounty directly (title, description, point value), starting it in the open state and recording which parent created it. Add a test confirming a child account cannot reach the same endpoint.

## 16. Weekly Reset Management Command
Goal: Automatically repopulate the board from active chore templates.
Description: Add a management command that creates one new open bounty per active chore template, intended to run weekly via cron. Add a test running the command twice and asserting it doesn't skip active templates or misbehave on repeated runs, and note the intended schedule in the command's docstring.

## 17. Claim-Expiry Sweep (Command + Lazy Check)
Goal: Return unfinished claimed chores to the board after the claim window expires.
Description: Add a management command, intended to run every few minutes via cron, that resets any claimed bounty whose claim timer has passed back to open. Also add the equivalent check inside the bounty board view so an expired claim reverts as soon as someone loads the board, even between cron runs, with tests covering both paths.

## 18. Perk Store Browsing & Purchase Action (HTMX)
Goal: Let a user spend points on a perk.
Description: Add a view listing active perks alongside the signed-in user's current balance, and an HTMX purchase action that creates a locked purchase if the user has enough points. Reject the purchase with a clear message if the balance is insufficient.

## 19. Parent Fulfillment Queue & Fulfill Action (HTMX)
Goal: Let a parent mark a purchased perk as delivered and finalize the point spend.
Description: Add a parent-only view listing all locked purchases, with a Fulfill action that marks the purchase fulfilled, records a debit in the point ledger, and updates the buyer's cached balance. Add a test confirming a child account cannot reach the fulfillment endpoint.

## 20. Points Balance Header Component
Goal: Show a user's current point balance on every page, kept live via HTMX.
Description: Add a small template partial displaying the signed-in user's points balance in the site's base template/header. Wire the point-changing actions (claiming's approval step, purchasing, fulfilling) to include an HTMX out-of-band swap so the header balance updates automatically after any action that changes it, without a full page reload.

## 21. Dev Seed Data
Goal: Make the app usable out of the box for local development and demos.
Description: Add a management command or fixture that creates a few sample chore templates, a few sample perks, and one parent plus one child test account, so a new developer can run the app and immediately see a populated board. Add a short section to the README explaining how to run it.
