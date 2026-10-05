# QA Review — b0aecd1 `test(e2e): walk journeys T-1, T-2, T-3 and close Phase T`

Reviewed 2026-10-05. Scope: the last commit only — `tests/e2e/t-1-tracer-walk.md` (edited),
`t-2-same-slot-race.md` and `t-3-abandoned-hold.md` (new). Docs-only; no code changed.

## Status: ✅ PASS — follow-ups F-1 and F-2 DONE

## What I verified

| Claim | How | Result |
|---|---|---|
| Suite is 49 green | `bench --site apnaslot.localhost run-tests --app apna_slot` | ✅ `Ran 49 tests … OK` |
| Error and UI texts the scripts assert exist | grep against `exceptions.py`, `venue.py`, `Pay.vue`, `VenuePage.vue` | ✅ all match word for word |
| `test_publish_refuses_a_venue_with_no_resource` exists (T-1 step 7) | `tests/test_tracer.py:164` | ✅ |
| `*/2` sweep `expire_pending_bookings` exists; scheduler is on | `hooks.py:40`, `scheduler status` | ✅ |
| `bench serve` on :8000 pins to `default_site` | `curl` :8000 → 404, :8001 → 200; `common_site_config` has `default_site: site1.local` | ✅ the note is correct |
| **T-2 replayed live** (sessions `qa-a`, `qa-b`, venue `green-field-sports-arena-3`, 6 Oct 19:00) | agent-browser | ✅ every step |
| ↳ A clicks 19:00 | lands on `/checkout/BKG-2026-00046` | ✅ |
| ↳ B clicks its stale 19:00 | stays on the venue page; "19:00 on 6 Oct is no longer available. Pick another slot."; the grid refreshes and 19:00 reads **Booked**, disabled | ✅ |
| ↳ B POSTs `booking.create` | HTTP 409 `SlotUnavailableError`, same message | ✅ |
| ↳ Ledger | one `Booking Slot` row at 19:00, owned by A; B has 0 bookings | ✅ |
| ↳ dark, 375px, console on B's grid | no horizontal overflow (`scrollWidth` 375), readable in dark mode, no console errors | ✅ |
| **T-3 replayed live** on the same booking | agent-browser + SQL | see below |
| ↳ steps 1–3: Pay → Abandon → reopen `/pay/:token` | lands on `/apnaslot/`; booking `Pending Payment`, one ledger row; "This payment is already abandoned.", no buttons | ✅ |
| ↳ step 4: grid from B before the hold lapses | 19:00 reads **Booked** | ✅ |
| ↳ steps 5–7: after the sweep | hold lapsed at 12:42:46 UTC and the booking read `Expired` at 12:48 (see the scheduler observation below); `hold_expires_at` cleared, 0 ledger rows; 19:00 shows as available on B's grid; My Bookings shows the `Expired` badge; no console errors | ✅ |
| Earlier walks left a trail | 3 earlier `Abandoned` payments (BKG-…27, …33, …40) are all `Expired` with 0 ledger rows | ✅ |

## Findings

### F-1 (minor, product gap left untracked) — sign-up drops `?redirect` — ✅ DONE

T-1 step 12 now says "the login → signup link drops `?redirect`; the round trip is journey 5-2".
The cause is a one-liner: `frontend/src/pages/Login.vue:55` links to `/signup` without
`route.query.redirect`, though `SignUp.vue:16` already honours one. But journey 5-2 and
`phase-5-customer-experience.md` §7 only describe **log in** → return; neither mentions sign-up, and
PROGRESS.md does not list it. As written, the defect is recorded in one e2e note and owned by no
phase. A new customer who clicks a slot while signed out and then signs up lands on `/`, not the
venue — the first-booking path from the T-1 key assertion.

**Fix:** forward the query on the link (`:to="{ path: '/signup', query: route.query }"`), or at
least add sign-up to journey 5-2 / phase 5 §7 so it has an owner.

**Done:** Login and SignUp links both forward `route.query`; T-1 step 12 now asserts the round trip.

### F-2 (minor, docs) — scripts point at a port that does not serve this site here — ✅ DONE

The T-2 commands and every URL in T-1/T-3 use `apnaslot.localhost:8000`. The new driving note (and
`03-testing.md` §3) says this bench must serve on `:8001`, where `:8000` returns 404. T-2 and T-3 do
not reference the note, so anyone replaying them alone hits 404s first. Add a one-line pointer to
the serve note in T-2/T-3, or use a `$BASE` variable set once.

**Done:** T-2 and T-3 point at the serve note; T-2 step 5 spells out the `booking.create` payload.

### Observations (no action needed for this commit)

- T-2 step 5 / T-1 step 14 don't give the `booking.create` payload. A wrong shape (e.g. `lines: [...]`)
  returns HTTP 500 `TypeError` rather than a 4xx. Worth writing out
  `{resource, slot_date, start_time}` in the script.
- My first sign-up click in one session went nowhere because I clicked before the page settled — a
  driving issue, not the app; a `wait --load networkidle` before filling is enough. On retry it
  worked.
- When I reviewed, no `bench schedule` or worker was running: the last sweep ran at 12:32 UTC, and
  the hold sat past its expiry until I started both. After that it expired within one tick. T-3
  already says it needs both, but `scheduler status` reports "enabled" even when nothing is
  running. Step 0 could check the processes instead, e.g. `ps aux | grep 'frappe schedule'`.
- T-3's SQL reads `hold_expires_at` after expiry, but expiry sets it to NULL. Note it at step 2, as the
  script says.
- T-1 step 7 is now marked unreachable from the UI and owned by a unit test until the Phase 1 wizard
  exists — that's a reasonable call, and the test is there.
