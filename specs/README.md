# Apna Slot — Specifications

Multi-tenant venue slot booking platform built on Frappe Framework v16.

Publishers (turf owners, court operators, hall managers) list venues and the bookable
resources inside them, define opening hours and time-based pricing, and publish. Customers
discover venues, pick one or more slots on a fixed grid — several times in a day, or the same time
across several weeks — pay once, and hold a confirmed, exclusive booking.

## How to read these specs

Read in this order. The first five documents are cross-cutting and are referenced by every phase
document — do not skip them.

| # | Document | What it is |
|---|---|---|
| — | [00-domain-model.md](./00-domain-model.md) | Every entity, its relationships, the glossary, and the system-wide invariants. The single source of truth for naming. |
| — | [01-decisions.md](./01-decisions.md) | The 33 design decisions behind this system, each with the alternatives that were rejected and why. Read before proposing a change. |
| — | [02-conventions.md](./02-conventions.md) | Module layout, where classes earn their place, function and file size, naming, reuse, error handling. |
| — | [03-testing.md](./03-testing.md) | The four test layers, the rules that keep the suite honest, and the agent-browser E2E journeys. |
| — | [04-workflow.md](./04-workflow.md) | Conventional commits, branches, PRs, spec reconciliation, bench commands. |
| — | [PROGRESS.md](./PROGRESS.md) | What is actually built. Updated every step. |
| **T** | [phase-t-tracer.md](./phase-t-tracer.md) | **The tracer bullet.** One thin end-to-end path through every layer, with the six architectural bets it settles. Build this first. |
| 0 | [phase-0-foundations.md](./phase-0-foundations.md) | Module setup, Publisher + team, roles and permission isolation, taxonomies, auth, SPA scaffold. |
| 1 | [phase-1-listing.md](./phase-1-listing.md) | Venue, Bookable Resource, weekly schedule, closures, rules and amenities, publisher CRUD screens. |
| 2 | [phase-2-pricing.md](./phase-2-pricing.md) | Price rules, the resolver, quoting, pricing UI with live preview. |
| 3 | [phase-3-booking-engine.md](./phase-3-booking-engine.md) | Availability computation, Booking + Booking Line + Booking Slot ledger, multi-date series, the hold, expiry job, the concurrency invariant. |
| 4 | [phase-4-mock-payments.md](./phase-4-mock-payments.md) | Payment gateway abstraction, MockGateway, fake hosted checkout, callback, commission. |
| 5 | [phase-5-customer-experience.md](./phase-5-customer-experience.md) | Discovery and search, venue page, availability grid, checkout, My Bookings. |
| 6 | [phase-6-lifecycle.md](./phase-6-lifecycle.md) | Per-line and whole-booking cancellation, mock refunds, venue-side cancellation, email templates, reminders. |
| 7 | [phase-7-future.md](./phase-7-future.md) | Not built. Real gateway swap, payouts, and every deferred flag with its unblocking cost. |

## Phase ordering rationale

**Phase T fires first.** A tracer bullet is a thin vertical slice through every layer, built to
find out where the architecture actually lands before the expensive work starts. Phase T ships
signup → publisher → venue → one resource → one slot → booking → mock payment → confirmation →
My Bookings, complete with the `Booking Slot` unique index that *is* the double-booking guarantee.
It is not a prototype: every line survives into Phase 6. It omits breadth, never depth.

Phases 0–6 then **thicken** that skeleton. Each is independently shippable and independently
testable, and each opens with a note saying what Phase T already delivered.

The booking engine (Phase 3) is deliberately specified **before** payments (Phase 4) so that the
concurrency invariant — the hardest and most important property in the system — is provable in
isolation, without gateway callbacks tangled into the test. Phase T settles that invariant even
earlier, which is the whole reason it exists.

## Conventions used throughout

- **App**: `apna_slot`. **Modules**: `Apna Slot Core`, `Apna Slot Booking` (see
  [02-conventions.md](./02-conventions.md) §1). **Site**: `apnaslot.localhost`.
- All bench commands pass `--site apnaslot.localhost` explicitly.
- DocType field tables list: fieldname, fieldtype, options, and notes. `reqd` and `default` are
  called out in notes.
- API signatures are given as `apna_slot.api.<module>.<method>` — the dotted path used by
  `/api/method/…` and by frappe-ui's `useCall`.
- Times written as `HH:MM` are **venue-local wall-clock**. Anything in UTC is named `*_utc`.
- Money is always in the venue's currency. There is no conversion anywhere in the system.
- A **booking** is one resource and one or more dated **lines**; a weekly series is one booking with
  several lines, not several bookings (D-28).
- Diagrams are [mermaid](https://mermaid.js.org) fenced blocks. GitHub, VS Code (with the built-in
  markdown preview) and most markdown viewers render them inline; a plain text editor shows the
  source, which is still readable.
