# Testing Strategy

CLAUDE.md: *"Always write tests, and make sure they work"* and *"Use agent-browser to test e2e."*
This document says which kind of test proves which kind of claim, and gives the runnable commands.

Each phase document already carries its own test table. This file is the layer above them: the
shape of the suite, the rules that keep it honest, and the browser journeys.

---

## 1. Four layers, four jobs

| Layer | Proves | Where | Runner |
|---|---|---|---|
| **Unit** | Pure logic: price resolution, slot generation, series expansion, timezone conversion, selection state | `tests/test_<phase>.py` (Python), `frontend/src/lib/*.test.js` (JS) | `run-tests` / `vitest` |
| **Integration** | Controllers, permissions, APIs, jobs — everything that touches the database | `tests/test_<phase>.py` on `FrappeTestCase` | `run-tests` |
| **Concurrency** | I-1 only. Two real connections racing for one slot | `tests/test_tracer.py`, `tests/test_phase3.py` | `run-tests` |
| **E2E** | The user's journey through the real SPA against the real site | `tests/e2e/*.md` journeys, driven by agent-browser | agent-browser |

The pyramid is deliberately bottom-heavy. The E2E layer is for **journeys**, not for coverage: it
proves the screens are wired to the APIs, not that the pricing ladder is correct.

---

## 2. Rules that keep the suite honest

1. **A test that cannot fail is not a test.** Before committing a test, break the code it covers and
   watch it go red. This applies most to the invariant tests — a concurrency test written with two
   sequential calls passes against code with no guarantee at all.
2. **Concurrency tests use two real database connections** — threads each calling `frappe.connect`.
   Stated in Phase 3 and repeated here because it is the single most likely thing to be quietly
   downgraded.
3. **Query budgets are asserted, not hoped for.** `test_multi_day_grid_query_budget` and
   `test_quote_query_budget_flat_across_dates` assert *counts*. The batching rules in Phases 2 and 3
   are load-bearing and silently regress otherwise.
4. **Time is injected, never slept.** Freeze `frappe.utils.now_datetime` or pass explicit
   timestamps. No test waits 10 minutes for a hold. The expiry job is tested by moving
   `hold_expires_at` into the past, not by waiting.
5. **Timezone tests use two timezones.** A single-timezone assertion passes on a system that
   ignores timezones entirely. Every UTC test runs against `Asia/Dubai` **and** `Asia/Kolkata`, and
   DST tests against `Europe/London`.
6. **Permission tests assert the empty case.** "Non-member sees nothing" needs the fail-closed
   assertion (`1=0`, empty list), not just "member sees their own".
7. **Fixtures live in one place.** `tests/fixtures.py` builds a publisher, venue, resource and
   customer through the real controllers — never with `frappe.db.set_value` shortcuts that skip the
   validation the test is implicitly relying on.
8. **Every invariant I-1…I-10 has at least one named test**, and the test names it in a docstring.
   [00-domain-model.md](./00-domain-model.md) is the checklist.

---

## 3. Commands

```bash
# One phase
bench --site apnaslot.localhost run-tests --app apna_slot --module apna_slot.tests.test_tracer

# Everything
bench --site apnaslot.localhost run-tests --app apna_slot

# One test
bench --site apnaslot.localhost run-tests --app apna_slot \
  --module apna_slot.tests.test_phase3 --test test_concurrent_booking_same_slot_one_wins

# Frontend units
cd apps/apna_slot/frontend && yarn test
```

`bench start` must be running for E2E. Start it in the background only if it is not already up.

---

## 4. End-to-end with agent-browser

### Setup, once per run

```bash
export AGENT_BROWSER_SESSION="$(agent-browser session id --scope worktree --prefix apnaslot)"
agent-browser open http://apnaslot.localhost:8000/apnaslot
agent-browser snapshot -i
```

The core loop is **open → `snapshot -i` → act on `@eN` → re-snapshot**. Refs go stale on every page
change, so re-snapshot after each click that navigates. Wait explicitly
(`wait --url`, `wait --text`, `wait --load networkidle`) — never `wait 2000`.

Two customers racing for one slot need **two isolated sessions**, each with its own cookies:

```bash
agent-browser --session customer-a open http://apnaslot.localhost:8000/apnaslot/venues/green-field-sports-arena
agent-browser --session customer-b open http://apnaslot.localhost:8000/apnaslot/venues/green-field-sports-arena
```

Finish with `agent-browser close --all`.

### Journeys

Each journey is a markdown file in `apna_slot/tests/e2e/` with numbered steps and the exact
assertion at each one — a script a human or an agent can replay identically. Screenshots go to
`tests/e2e/screenshots/` and are **not** committed.

| ID | Phase | Journey | Key assertions |
|---|---|---|---|
| **T-1** | T | Sign up → create publisher → create + publish venue with one resource → sign up as a second user → book one slot → mock pay Succeed → see it in My Bookings | booking `Confirmed`; slot reads `Booked` on reload |
| **T-2** | T | Two sessions, same slot: A books and reaches checkout; B tries the same slot | B is refused with a specific message; B's grid shows it booked; exactly one booking exists |
| **T-3** | T | Book → mock pay **Abandon** → wait past the hold → reload the grid | slot is available again; booking is `Expired` |
| **0-1** | 0 | Publisher A logs in and attempts B's venue URL directly | 403/404, never B's data |
| **1-1** | 1 | Venue wizard end to end, including the schedule builder with a split shift and a deliberate 06:00–12:30 misconfiguration | the validation error names the offending row; the live slot preview updates |
| **1-2** | 1 | Publish a venue with no base price | banner lists exactly what is missing; each item deep-links |
| **2-1** | 2 | Add a weekend rule, then a weekend-evening band, then a single-date holiday rule | the price calendar shows all three winning on the right days; the rules list orders by effective priority |
| **3-1** | 3 | Select two **non-adjacent** slots on one date | one booking, two lines, both slots booked |
| **3-2** | 3 | `Repeat weekly × 6` with week 3 pre-booked | week 3 shows unavailable and unchecked; booking the other five creates five lines |
| **4-1** | 4 | Pay → **Fail** | slot free immediately; booking `Payment Failed` |
| **4-2** | 4 | Let the checkout countdown reach zero | page stops polling, shows "This hold has expired", offers a route back to the grid |
| **5-1** | 5 | Search by city, add two amenities, copy the URL into a second session | identical result set; AND semantics narrow the list |
| **5-2** | 5 | Guest clicks *Book now* → logs in → returns | the same venue, date and selection survive the round trip |
| **5-3** | 5 | Select slots at 375px width | no horizontal page scroll; sticky summary bar usable |
| **6-1** | 6 | Cancel two dates of a six-date series | those two rows update in place, refund appears, booking stays `Confirmed` with "2 of 6 dates cancelled" |
| **6-2** | 6 | Attempt to cancel a line inside the policy window | inline reason on that row; other rows stay selectable |

### Every journey also checks

- **Dark mode.** frappe-ui's Tailwind preset uses `darkMode: ['selector', '[data-theme="dark"]']`,
  so the theme is an **attribute on `<html>`, not a `dark` class** — toggling a class changes
  nothing and silently passes a broken check:

  ```bash
  agent-browser eval "document.documentElement.setAttribute('data-theme','dark')"
  agent-browser screenshot dark.png
  ```

  Re-run the final screen that way; no unreadable text, no hard-coded colour leaking through.
- **Console.** No errors. `agent-browser console` after the journey.
- **375px.** At least one journey per frontend phase runs narrow.

### Reporting a run

A journey passes only when every numbered assertion passes. Record failures as
`journey-id · step · expected · actual · screenshot path`, and fix the code — never the journey —
unless the spec itself was wrong, in which case amend the spec first
(see [04-workflow.md](./04-workflow.md)).

---

## 5. Definition of done for a phase

A phase is not done until all five hold:

1. Every test in the phase's test table exists and passes.
2. Every acceptance criterion in the phase document has been observed to hold.
3. Every E2E journey for the phase passes, in light and dark.
4. `bench --site apnaslot.localhost run-tests --app apna_slot` is green — **all** phases, not just
   the new one.
5. [PROGRESS.md](./PROGRESS.md) is updated and the phase document reconciled against what was
   actually built.
