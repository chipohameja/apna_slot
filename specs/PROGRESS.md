# Implementation Progress

Single source of truth for *what is built*. Update it at the end of every step, not at the end of
every phase. If this file and the code disagree, the code is right and this file is a bug.

**Status legend:** ☐ not started · ◐ in progress · ☑ done (tests + E2E green) · ⊘ deferred

Last updated: 2026-09-07 · Phase T steps T-a to T-d done. **R1, R2, R3 and R4 settled.** The
ledger holds: a customer books a slot through the SPA, the hold blocks everyone else, and two
concurrent connections racing for one slot leave exactly one booking and one ledger row.

---

## Phase summary

| Phase | Document | Status | Ships |
|---|---|---|---|
| **T** | [phase-t-tracer.md](./phase-t-tracer.md) | ◐ | Walking skeleton: signup → venue → one slot → mock pay → confirmed, with the unique index |
| 0 | [phase-0-foundations.md](./phase-0-foundations.md) | ☐ | Taxonomies, team management, full permission matrix |
| 1 | [phase-1-listing.md](./phase-1-listing.md) | ☐ | Full listing surface, closures, schedule builder |
| 2 | [phase-2-pricing.md](./phase-2-pricing.md) | ☐ | Price rules, resolver, pricing calendar |
| 3 | [phase-3-booking-engine.md](./phase-3-booking-engine.md) | ☐ | Multi-slot, multi-date, series, closures + DST in the grid |
| 4 | [phase-4-mock-payments.md](./phase-4-mock-payments.md) | ☐ | Commission, idempotency, expiry-beats-success |
| 5 | [phase-5-customer-experience.md](./phase-5-customer-experience.md) | ☐ | Discovery, selection UI, publisher calendar |
| 6 | [phase-6-lifecycle.md](./phase-6-lifecycle.md) | ☐ | Cancellation, refunds, emails, reminders |
| 7 | [phase-7-future.md](./phase-7-future.md) | ⊘ | Not built by design |

---

## Architectural bets (Phase T)

The six risks Phase T exists to retire. None is settled until its test is green.

| Bet | Claim | Test | Status |
|---|---|---|---|
| R1 | The unique index is a sufficient double-booking guarantee | `test_concurrent_booking_same_slot_one_wins` | ☑ two connections, both past the pre-check; dropping the index turns the test red with two winners |
| R2 | Wall-clock + denormalised UTC round-trips through `ZoneInfo` | `test_line_utc_matches_venue_timezone` | ☑ Dubai 19:00 → 15:00Z, Kolkata 19:00 → 13:30Z, on a site running `Africa/Kigali` |
| R3 | Permission hooks isolate tenants and fail closed | `test_query_conditions_fail_closed_for_non_member` | ☑ also proven on `Venue`: list, document read, and creating a resource under another tenant's venue |
| R4 | Hand-scaffolded frappe-ui SPA builds, serves, authenticates on cookies | E2E journey T-1 | ☑ builds, serves, and authenticates on cookies; no console errors, light and dark, 375px |
| R5 | Gateway interface + signed callback drives the state machine | `test_callback_confirms_booking` | ☐ |
| R6 | The scheduled job releases abandoned holds | `test_expiry_job_releases_hold` | ☐ |

---

## Phase T — Tracer bullet

| Step | Deliverable | Status |
|---|---|---|
| T-a | `hooks.py`, two modules, `www/apnaslot.py`, route rules, Vite + Tailwind + frappe-ui scaffold serving one page | ☑ |
| T-b | `Publisher` + `Publisher Member`, `permissions.py`, signup/session APIs, login + signup + onboarding screens | ☑ |
| T-c | `Venue`, `Bookable Resource`, `Resource Schedule Row`, publish, `api.discovery.search_venues`, publisher venue list + bare create form, public list | ☑ |
| T-d | `Booking Slot` + unique-index patch, `Booking` + `Booking Line`, `AvailabilityGrid`, `PriceResolver`, `create_booking`, `get_venue`, venue page with day grid, checkout shell | ☑ |
| T-e | Gateway ABC, `MockGateway`, `Payment Transaction`, start/callback, checkout + mock-pay screens, `confirm_booking` | ☐ |
| T-f | `expire_pending_bookings`, `release_booking`, My Bookings | ☐ |
| T-x | `tests/test_tracer.py` green; E2E journeys T-1, T-2, T-3 pass | ☐ |

## Phase 0 — Foundations

| Step | Deliverable | Status |
|---|---|---|
| 0-a | `Activity Type` + `Amenity` doctypes and fixtures | ☐ |
| 0-b | Publisher fields completed: `commission_percent`, `payout_details`, `contact_phone` | ☐ |
| 0-c | `member_role` permission gradations (Owner / Manager / Staff) in `has_permission` | ☐ |
| 0-d | `add_member` / `remove_member` APIs + Team screen | ☐ |
| 0-e | Publisher Settings screen, onboarding redirect guard | ☐ |
| 0-x | `tests/test_phase0.py` green; E2E journey 0-1 | ☐ |

## Phase 1 — Listing

| Step | Deliverable | Status |
|---|---|---|
| 1-a | Venue content fields: description, images, amenities, rules, geo, contact | ☐ |
| 1-b | Venue policy fields + `free_cancellation_hours`, publishability checks, `published_on` | ☐ |
| 1-c | Resource completion: `activity_type`, images, `duplicate_resource` | ☐ |
| 1-d | `Resource Closure` + overlap warning | ☐ |
| 1-e | Venue wizard, tabbed detail, schedule builder with live slot preview, publish banner | ☐ |
| 1-x | `tests/test_phase1.py` green; E2E journeys 1-1, 1-2 | ☐ |

## Phase 2 — Pricing

| Step | Deliverable | Status |
|---|---|---|
| 2-a | `Resource Price Rule` child table + validation + auto-priority | ☐ |
| 2-b | `PriceResolver` grows rule matching (replaces the T stub body) | ☐ |
| 2-c | `quote()` across dates; `get_quote` / `preview_calendar` / `preview_day` APIs | ☐ |
| 2-d | Pricing tab: rules list, rule editor, live price calendar | ☐ |
| 2-x | `tests/test_phase2.py` green; E2E journey 2-1 | ☐ |

## Phase 3 — Booking engine

| Step | Deliverable | Status |
|---|---|---|
| 3-a | Grid completion: closures, DST skip/fold, window statuses, `for_dates()` batching | ☐ |
| 3-b | Multi-line `create_booking` with all-or-nothing rollback and `conflicting_lines` | ☐ |
| 3-c | `expand_weekly_series`, `preview_series` API | ☐ |
| 3-d | `release_line`, roll-ups, `complete_past_lines` hourly job | ☐ |
| 3-e | Controller guards: transitions, I-3 shape, I-7 immutability | ☐ |
| 3-x | `tests/test_phase3.py` green; E2E journeys 3-1, 3-2 | ☐ |

## Phase 4 — Mock payments

| Step | Deliverable | Status |
|---|---|---|
| 4-a | Commission snapshot at confirmation (I-10) | ☐ |
| 4-b | Callback idempotency + expiry-beats-success refund path | ☐ |
| 4-c | `payment.start` reuse, token handling, rate limiting | ☐ |
| 4-d | Real checkout screen with line table, rules acknowledgement, server-anchored countdown | ☐ |
| 4-e | Delete `confirm_internal` | ☐ |
| 4-x | `tests/test_phase4.py` green; E2E journeys 4-1, 4-2 | ☐ |

## Phase 5 — Customer experience

| Step | Deliverable | Status |
|---|---|---|
| 5-a | `search_venues` with filters, sort, pagination; `get_filter_options` | ☐ |
| 5-b | Home + discovery with URL-encoded filters and named empty states | ☐ |
| 5-c | Venue page: gallery, resource selector, date strip, slot grid | ☐ |
| 5-d | `src/lib/slotSelection.js` (`toggleSlot`, `expandWeekly`, `dropConflicts`) + unit tests | ☐ |
| 5-e | Cross-date selection chips, repeat-weekly builder, sticky summary, 409 conflict handling | ☐ |
| 5-f | My Bookings, booking detail, publisher booking list + calendar | ☐ |
| 5-x | `tests/test_phase5.py` green; E2E journeys 5-1, 5-2, 5-3 | ☐ |

## Phase 6 — Lifecycle

| Step | Deliverable | Status |
|---|---|---|
| 6-a | `Refund` + `Refund Line`, `gateway.refund()` | ☐ |
| 6-b | `cancel_by_customer` / `cancel_by_venue` + `get_cancellation_policy` | ☐ |
| 6-c | Money recomputation on partial cancellation (I-10) | ☐ |
| 6-d | Email templates + `notifications.py` | ☐ |
| 6-e | `send_booking_reminders` job, per-line idempotency | ☐ |
| 6-f | Cancellation UI: per-line checkboxes, refund preview, closure-driven cancel | ☐ |
| 6-x | `tests/test_phase6.py` green; E2E journeys 6-1, 6-2 | ☐ |

---

## Invariant coverage

Every invariant in [00-domain-model.md](./00-domain-model.md) needs a passing test before the phase
that introduces it is done.

| Invariant | Introduced | Test | Status |
|---|---|---|---|
| I-1 Exclusivity | T | `test_concurrent_booking_same_slot_one_wins` | ☑ |
| I-2 Ledger correspondence | T | `test_expiry_job_releases_hold`, `test_completion_keeps_ledger_rows` | ☐ |
| I-3 Booking shape | 3 | `test_duplicate_line_in_request_rejected`, cap tests | ☐ |
| I-4 Schedule containment | 3 | `test_grid_marks_closed_whole_day` | ☐ |
| I-5 Booking window | 3 | `test_series_beyond_advance_window_rejected` | ☐ |
| I-6 Price snapshot | 2 | `test_price_edit_does_not_alter_existing_booking` | ☐ |
| I-7 Post-confirmation immutability | 3 | `test_confirmed_booking_lines_immutable` | ☐ |
| I-8 Tenant isolation | T | `test_query_conditions_fail_closed_for_non_member` | ☑ |
| I-9 Snapshot immutability | T | `test_line_utc_matches_venue_timezone` | ☑ |
| I-10 Money reconciliation | 4 | `test_success_confirms_and_snapshots_commission` | ☐ |

---

## Open questions

Things the specs do not yet answer. Add here rather than deciding silently mid-build; promote to a
`D-nn` entry in [01-decisions.md](./01-decisions.md) once settled.

| # | Question | Blocks | Status |
|---|---|---|---|
| Q-1 | Module naming — the symmetric `Apna Slot Core` / `Apna Slot Booking`. | T-a | **settled** in T-a |
| Q-2 | Does the `Venue` permission query's `OR status = 'Published'` clause need a separate read path for guests, or does one condition serve both publisher and public listing? | T-c | **settled** as [D-34](./01-decisions.md): a separate read path. `tenant_query` stays fail-closed; `api.discovery` owns the public one. |

---

## Notes from the build

Things learned while building that the phase documents now record.

- **T-a.** The frappe-ui vite plugin derives D-27's whole build contract from `frontendRoute` alone,
  and generates `www/apnaslot.html` itself — so that file and `public/frontend` are both build
  artefacts, and the hand-written half is `www/apnaslot.py` supplying `context.boot`.
- **T-a.** Renaming the default module left a stale `Module Def` row pointing at the old dotted
  path, which fails `migrate` with `ModuleNotFoundError` until the cache is cleared and the row
  removed. Do the module split before the first DocType exists, as D-33 says.
- **T-a.** Dark mode is `data-theme="dark"` on `<html>`, not a `dark` class — see
  [03-testing.md](./03-testing.md) §4. Screenshot *after* the attribute flip settles: the theme
  transition is animated, and a shot taken immediately catches unreadable mid-transition colours.
- **T-b.** Roles cannot be created by the DocType JSON that references them. They ship as
  `apna_slot/fixtures/role.json`, which `migrate` imports after the doctype sync; that ordering is
  safe only because DocType import sets `ignore_links`.
- **T-b.** Every session change leaves the SPA via `window.location.href`. A new session carries a
  new CSRF token, and only a full page load re-renders `www/apnaslot.py`'s boot data with it.
- **T-b.** `FormControl` applies its `class` to the wrapper, not to the control, so
  `type="select"` / `type="combobox"` stay content-width in a form of full-width inputs. The
  library's own idiom is `<Select class="w-full">` next to a `FormLabel`.
- **T-b.** Running the suite needs `bench --site apnaslot.localhost set-config allow_tests true`
  once.
- **T-c.** Frappe seeds a new document's defaults from *user defaults keyed by fieldname*, so any
  field called `currency` arrives pre-filled with the site's default currency. A venue therefore
  cannot inherit its publisher's currency with `self.currency = self.currency or ...` — the field is
  never empty. It is claimed outright in `before_insert`.
- **T-c.** `Document.insert()` runs `check_permission("create")` **before** `_validate_links()`
  fetches `fetch_from` values, so a new `Bookable Resource` has no `publisher` yet when
  `has_permission` fires. `permissions.publisher_of()` resolves the tenant through `venue` for
  exactly that window; every later doctype that denormalises `publisher` inherits the fix.
- **T-c.** frappe-ui composes a failed call's message as `${type}: ${message}`, so the raw
  exception class name reaches the form. `frontend/src/lib/errors.js` strips it —
  [02-conventions.md](./02-conventions.md) §7 asks the message to name the thing and the next
  action, and "ValidationError:" is neither.
- **T-c.** Tests must not assume an empty site. Two slug assertions passed alone and failed after
  the E2E walk created venues of the same name; they now derive their own unique name.
- **T-d.** *The tracer's biggest find.* The first race never reached the unique index: both threads
  collided on Frappe's `tabSeries` naming counter, which is held with `SELECT … FOR UPDATE` until
  the transaction ends. Any two Bookings created in the same instant contend there — different
  venues included. `claim()` now retries transient lock errors only. See
  [phase-3-booking-engine.md](./phase-3-booking-engine.md) §4.
- **T-d.** A `frappe.db.savepoint()` name is interpolated straight into SQL, so
  `frappe.generate_hash()` fails intermittently — roughly one name in three starts with a digit and
  is not a valid identifier. Frappe's own helper samples ASCII letters for exactly this reason.
- **T-d.** `raise SlotUnavailableError(...)` sends the browser the class name and nothing else;
  only `frappe.throw` puts a message in the response envelope. The customer-facing text now goes
  through `exceptions.refuse_slots()`, which also clears Frappe's internal "must be unique"
  message first.
- **T-d.** A `useCall` with `refetch: true` over params that start out null fires one doomed
  request per page visit. Drive a dependent call from an explicit `watch` instead.
- **T-d.** `frappe.utils.now_datetime()` is the *site's* timezone (`Africa/Kigali` here), not UTC.
  Every instant this app writes comes from `utils.timezone.utc_now()`; the mismatch would have been
  invisible on a UTC site.
