# Design Decisions

Every decision below was settled deliberately. Each records the alternatives that were rejected
and why. **Read the relevant entry before proposing a change** — most "obvious simplifications"
here are things that were considered and turned down for a stated reason.

Status legend: **Settled** — decided, build it this way. **Reserved** — a schema affordance
exists, the behaviour is deliberately not built.

---

### D-1 — Two-level hierarchy: Venue → Bookable Resource · *Settled*

A venue contains multiple bookable things with different hours, capacity and prices (Turf A,
Turf B, a badminton court). Availability and pricing hang off the **resource**; address, photos,
rules and policy hang off the **venue**.

*Rejected:* a flat model where a property *is* the bookable thing. It looks simpler for about a
week, then forces a schema migration the first time someone lists a venue with two courts —
which is the normal case for turf, not an edge case.

### D-2 — Instant confirmation only · *Settled* (request-to-book *Reserved*)

Paying confirms the booking immediately. `Bookable Resource.requires_approval` exists as a
hidden field defaulting to 0 and is not honoured by any code path.

*Rejected:* request-to-book. It doubles the state machine, needs authorise/capture semantics a
mock gateway cannot honestly model, and needs expiry-on-no-response.

### D-3 — One frappe-ui SPA with two routed areas · *Settled*

`/apnaslot/*` is public/customer, `/apnaslot/manage/*` is the publisher dashboard. Desk is for
the platform admin only.

*Rejected:* publishers in Desk. It's free UI and correct permissions, but it exposes the entire
framework to a turf owner who wants to change a price. *Rejected:* two separate SPAs — duplicate
build config, auth and component library for two areas that share most of their primitives.
*Accepted cost:* publisher CRUD screens are the single largest chunk of frontend work.

### D-4 — Login required to book · *Settled*

Email + password signup in Phase 0. No guest booking.

*Rejected:* guest booking with a retrieval code. Friendlier at checkout, but it breaks "my
bookings", makes self-service cancellation impossible to authorise, and worsens the abuse story
around holds.

### D-5 — Fixed slot grid with multi-slot selection · *Settled* — **amended by D-28**

A resource declares `slot_duration_minutes`; the day is chopped into fixed slots; a customer
selects one or more slots up to `max_slots_per_booking` per date.

> **Amended.** This decision originally required selected slots to be **adjacent**. D-28 removed
> that restriction and extended selection across dates. The fixed grid itself is unchanged and
> still load-bearing for the unique index.

*Rejected:* flexible start times on a 15-minute increment with variable duration. Partial-overlap
arithmetic is where booking systems earn their worst bugs, and it makes the unique-index
guarantee (D-11) impossible. *Rejected:* publisher-named slot templates — a fixed grid with
per-band pricing (D-12) already expresses "Prime 19:00–20:00".

### D-6 — Full prepayment with a 10-minute hold · *Settled*

The booking is created in `Pending Payment`, **blocks its slots immediately**, and carries
`hold_expires_at = now + 10 minutes`. A scheduled job releases lapsed holds.

*Rejected:* blocking only after payment succeeds — two customers can then both reach the gateway
for the same slot and one gets a refund instead of a booking. *Rejected:* partial deposits — a
second money-state per booking for no Phase-1 benefit.

### D-7 — Self-serve publisher onboarding, no admin approval · *Settled*

Anyone can sign up, create a Publisher, and list venues. Venues start in `Draft` and go live when
the publisher explicitly publishes them. `Venue.status` carries an `Under Review` value that no
code path currently sets.

*Rejected:* an admin approval queue. It is real ongoing operational cost with no ops team to pay
it, and it is additive later.

### D-8 — Multi-currency and multi-timezone from day one · *Settled* — **user override**

The recommendation was single-currency/single-timezone with the schema left open. The user chose
full multi-tenancy of locale. Consequences are specified in
[00-domain-model.md](./00-domain-model.md) → *Time and timezone model* and *Currency model*, and
in D-9/D-10.

### D-9 — Local wall-clock is truth, UTC is denormalised · *Settled*

Each booking line stores venue-local `line_date` + `start_time` + `end_time` **and** computed
`start_utc` / `end_utc`; the parent rolls up `first_start_utc` / `last_end_utc`.

*Rejected:* UTC-only storage. Publishers author schedules in wall-clock, so a UTC-only store
converts on every read of every grid cell and breaks across DST. *Rejected:* local-only storage —
the reminder job ("everything starting in the next 2 hours, across all venues") would need N
conversions per run. *Accepted cost:* on DST transition days one local hour is skipped and an
ambiguous hour resolves to `fold=0`.

### D-10 — Per-venue currency, no conversion · *Settled*

*Rejected:* a platform base currency with stored exchange rates — only pays off when there is
cross-currency reporting to do, and it is additive (D-8 note). *Rejected:* customer-selected
display currency with live FX — needs a rate feed and creates "the price changed while I was
paying".

### D-11 — Hybrid availability: derived grid, materialised booked slots · *Settled*

Availability is computed on demand from schedule − closures − ledger. Each held or confirmed
booking writes one `Booking Slot` row per slot, under a **unique index on
`(resource, slot_date, start_time)`**.

*Rejected:* fully materialised slots — millions of empty rows and a job that must run before
anyone can book 90 days out. *Rejected:* fully derived — no atomic way to stop two simultaneous
checkouts. *Accepted cost:* cancelled/expired bookings must delete their ledger rows, so the
ledger is current-state only (invariant I-2).

### D-12 — Price rules resolved by highest priority, first match · *Settled*

A resource has `base_price` plus a child table of rules, each optionally scoped by day-of-week
set, time band and date range. Active matching rules sort by `priority` desc then `idx` asc; the
first wins; no match falls back to `base_price`. `priority` defaults from specificity so a
publisher who never touches it gets sane behaviour.

*Rejected:* pure most-specific-wins with no priority field — two equally specific rules leave the
publisher with no tiebreaker. *Rejected:* additive/stacking modifiers — that is how pricing
engines become unexplainable to the person who configured them.

### D-13 — Per-venue cancellation window with mock refund · *Settled*

`Venue.free_cancellation_hours` (default 24). Inside the window the customer self-cancels and a
`Refund` record is raised against the mock gateway. Outside it, self-cancellation is refused.

*Rejected:* no customer cancellation in Phase 1 — the slot stays blocked while a human answers
the phone, which defeats the ledger. *Rejected:* tiered 100/50/0% refunds — Phase 3+ nicety.
*Known limitation:* a mock refund proves nothing about a real one.

### D-14 — Availability controls: advance window, lead time, closures · *Settled*
### Buffer time and capacity > 1 · *Rejected*

Phase 1 ships `max_advance_days`, `min_lead_minutes`, and a `Resource Closure` doctype.

*Rejected:* buffer time between bookings — expressible by choosing a longer slot length.
*Rejected:* per-slot capacity > 1 — it destroys the unique-index guarantee (D-11) and turns every
conflict check into a counting query under a lock. It is a legitimate feature for a different
product (desks, classes), and its cost is documented in phase-7.

### D-15 — Rich-text description + structured amenities + structured rule lines · *Settled*

*Rejected:* free text only — amenities are what customers filter on, and mining filters out of
prose later is a migration nightmare. Structured rule lines let checkout render an explicit
acknowledgement list.

### D-16 — Gateway-shaped mock payment · *Settled*

A `PaymentGateway` Python interface with a `MockGateway` implementation, a `Payment Transaction`
doctype, a fake hosted checkout route with **Succeed / Fail / Abandon**, and a server-side
callback that verifies a signature and confirms the booking.

*Rejected:* a "Simulate payment" button that flips a status — it makes real gateway integration a
rewrite of the booking state machine rather than a new class behind an existing interface. The
Fail and Abandon buttons are load-bearing: abandonment is what exercises the hold-expiry job,
which is the component most likely to be silently broken.

### D-17 — Optimistic concurrency; the unique index is the guarantee · *Settled*

Check availability, insert ledger rows, let the index raise. Catch `DuplicateEntryError`, roll the
whole booking back in one transaction, return a retryable "that slot was just taken".

*Rejected:* `SELECT … FOR UPDATE` on the resource-day — serialises a popular venue's entire
Saturday behind one lock and invites deadlocks. *Rejected:* a Redis lock — puts correctness in a
cache that can be flushed. The pre-check exists only to produce a friendly error 99.9% of the
time; it is **not** the guarantee.

### D-18 — Non-submittable Booking with an explicit status field · *Settled*

*Rejected:* `is_submittable = 1`. Frappe's draft/submitted/cancelled trio cannot express
`Expired` vs `Payment Failed` vs two flavours of cancellation, and `cancel()` is irreversible with
amendment ceremony attached. Immutability is obtained instead via controller guards (I-7).

### D-19 — Email notifications only · *Settled*

Frappe Email Template + Email Queue. Booking confirmed / cancelled / refunded, plus a reminder
2 hours before start driven by `start_utc`.

*Rejected:* no notifications — a booking nobody is reminded of is a no-show. *Rejected:*
SMS/WhatsApp — needs a paid vendor and credentials; it becomes another channel on the same
triggers later.

### D-20 — Discovery marketplace, no maps · *Settled*

Home page searches venues by city, activity type, amenities and price band.

*Rejected:* a map view — a Maps API key and per-load billing for a feature nobody needs before
there are 20 venues. *Rejected (worth revisiting):* direct-link-only, no discovery at all. It is
genuinely the cheaper, more focused product, and discovery is the largest single chunk of frontend
work in the plan. Multi-publisher marketplace was the stated intent, so discovery ships.

### D-21 — Organisation-based tenancy, not owner-based · *Settled*

A `Publisher` doctype with a member child table. Venues belong to a Publisher; permissions key off
membership.

*Rejected:* `owner`-based permissions. They break the first time a turf owner wants their manager
to also handle bookings — an early request, not an edge case. The Publisher record also gives
currency, timezone and commission a natural home. *Accepted cost:* one onboarding step ("create
your business") before a user can list anything.

### D-22 — Generic venue booking with a seeded taxonomy · *Settled*

`Activity Type` is a seeded fixture (football turf, cricket net, badminton court, tennis court,
banquet hall, studio, coworking desk). Turf is the first category, not the model.

*Rejected:* turf-specific fields on core doctypes. Nothing in the model is sport-specific and
genericity is free at this stage.

### D-23 — Commission computed and stored; no payouts module · *Settled*

`Publisher.commission_percent` → `Booking.commission_amount` + `publisher_payout_amount`,
snapshotted at confirmation.

*Rejected:* deferring commission entirely — retrofitting it means every historical booking has an
unknowable split. *Out of scope:* an actual settlement/payout ledger, which needs a real gateway.

### D-24 — Eight phases, booking engine before payments · *Settled* — **amended by D-32**

See [README.md](./README.md). Phase 3 confirms bookings internally so the concurrency invariant is
provable without gateway callbacks; Phase 4 rewires that call behind the payment callback.

*Accepted cost:* a small known rewire in Phase 4.

> **Amended.** D-32 puts a tracer bullet in front of all eight phases. Because Phase T ships the
> ledger *and* the payment callback in one slice, `confirm_internal` is never built and the Phase 4
> rewire is never needed — the accepted cost above is not paid. The *specification* order below is
> unchanged; only the build order is.

### D-25 — Per-phase files plus three cross-cutting documents · *Settled*

*Rejected:* flat per-phase files only — the invariants and vocabulary are referenced by every
phase and would drift across eight copies. *Rejected:* one monolithic `SPEC.md`.

### D-26 — Specs are implementation-ready · *Settled*

Every phase document carries full DocType field tables, exact API signatures with request/response
shapes, SPA routes with a frappe-ui component breakdown, acceptance criteria, and a named test
list.

*Rationale:* field-level decisions are where booking systems rot. A casual `Time` vs `Datetime`
choice in week 3 is the multi-timezone bug in month 6.

### D-27 — Cookie-session SPA, hand-scaffolded to pinned versions · *Settled*

Vite 5 + Vue 3 + Tailwind v3 + frappe-ui at `apna_slot/frontend`, built to
`apna_slot/public/frontend`, served at `/apnaslot` via `website_route_rules`, authenticated with
Frappe session cookies, all data access through `useCall` / `useList` / `useDoc`.

*Rejected:* token auth — CSRF and permissions already work exactly as Frappe intends with
cookies. *Rejected:* the Doppio / frappe-ui starter generator — it drifts from current pins and
leaves scaffolding to unpick.

---

### D-28 — One booking spans many slots and many dates, one resource · *Settled*

A booking covers **one resource** and any number of slots across any number of dates, paid for
together under one hold. Slots need not be adjacent. `Booking` therefore has no single date: it
carries a `Booking Line` child table, each line with its own date, times, `start_utc`, price and
status, and the parent keeps derived roll-ups (`first_start_utc`, `last_end_utc`,
`active_line_count`).

This is what makes the common turf case — *"7pm every Saturday for six weeks"* — a single booking
and a single payment.

*Rejected:* adjacent-only, same-date bookings (the original D-5 rule) — it forces six separate
bookings and six payments for a weekly series, which is the single most common repeat-customer
pattern in this market. *Rejected:* a **cross-venue cart**. Currency, timezone, publisher,
commission and cancellation policy are all per-venue and are snapshotted onto the booking; a cart
spanning venues needs a Booking Group above Booking, split payment across publishers, and a
checkout that shows two currencies and two cancellation policies at once. One resource per booking
keeps every snapshot valid. *Accepted cost:* the parent's date/time fields become derived, and both
scheduled jobs plus cancellation move to line granularity.

*Caps:* `max_slots_per_booking` (per date, default 4) and `max_dates_per_booking` (default 8) on
the resource. Longer commitments are season passes — Phase 7.

### D-29 — Multi-line booking is all-or-nothing · *Settled*

If any line of a requested booking collides, is closed, or falls outside the window, the whole
booking rolls back and the error lists the offending lines. The API returns
`conflicting_lines` so the UI can drop them and re-submit.

*Rejected:* partial success — silently booking four of six requested Saturdays. A customer who
believes they have six weeks and has four is a support ticket and a no-show; an error they can act
on is not.

### D-30 — Recurrence is expanded client-side, never stored · *Settled*

"Repeat weekly × 6" is a helper (`expand_weekly_series`) that produces concrete dates, which are
then checked for availability and stored as ordinary lines. No RRULE, no series document, no
recurring-booking engine.

*Rejected:* a stored recurrence rule. It immediately raises questions the product has no answers
for — how far into the future does it materialise, what happens when week 4 is closed, what does
the publisher see for a date that has not been generated yet, what happens when the rule is edited
after three weeks are played. Concrete lines have none of those questions.

### D-31 — Refunds are per cancellation event, covering specific lines · *Settled*

Cancelling two dates of a six-date series raises one `Refund` for exactly those two lines, with a
`Refund Line` child table naming them. `Booking.total_amount` never changes; `refunded_amount`
accumulates and `net_amount` follows, with commission recomputed against the net (I-10).

*Rejected:* one refund per booking (the original Phase 6 rule). Line-level cancellation makes that
impossible — and it is *needed*, because a venue closing for one Saturday must not have to cancel
the customer's other five. *Note:* this is bounded, line-derived partial refunding, not arbitrary
partial amounts; arbitrary partials remain deferred with deposits in Phase 7.

---

### D-32 — A tracer bullet precedes the eight phases · *Settled*

Phase T ([phase-t-tracer.md](./phase-t-tracer.md)) builds one thin vertical slice through every
layer — signup, publisher, venue, resource, availability grid, booking, ledger with its unique
index, mock payment, confirmation, My Bookings — before any phase builds breadth. Its scope is
chosen by **risk**: the six architectural bets (unique-index exclusivity, wall-clock/UTC round-trip,
fail-closed tenancy, the hand-scaffolded SPA, the gateway seam, the scheduled release job) each get
a named test in that phase.

*Rejected:* the original horizontal order — foundations, listing, pricing, engine, payments. It is
a comfortable order to write specs in and a dangerous one to build in: nothing is bookable until
Phase 4, so all six bets stay unvalidated through four phases of work built on top of them. If the
unique-index approach or the timezone model is wrong, the horizontal order finds out last.

*Rejected:* rewriting Phases 0–6 as vertical slices. The layered documents carry field-level
decisions that are the point of D-26, and re-cutting them would lose that detail to gain an
ordering that a single new phase plus a note on each existing one already achieves.

*Accepted cost:* seven of the eighteen DocTypes are created at a minimum field set in Phase T and
extended later, and each phase document must state what Phase T already delivered. Both are
mechanical. Nothing built in Phase T is thrown away — it is a walking skeleton, not a prototype.

### D-33 — Two modules: Apna Slot Core and Apna Slot Booking · *Settled*

The eighteen DocTypes are split into `Apna Slot Core` (Publisher, taxonomies, Venue, Bookable
Resource, closures, price rules — 12) and `Apna Slot Booking` (Booking, Booking Line, Booking Slot,
Payment Transaction, Refund, Refund Line — 6).

*Rationale:* CLAUDE.md caps a folder at ~15 files and Frappe requires all of a module's DocTypes in
one `doctype/` folder, so eighteen in one module breaks the rule outright. The split falls on a real
seam — inventory versus ledger — and not on an arbitrary line drawn to hit a number.

*Rejected:* one module with a documented exception to the 15-file rule. The exception would be
reasonable, but the seam exists anyway and naming it makes the permission model easier to read.
*Rejected:* three or more modules. Nothing else in the system is a genuine third concern; payments
and refunds are ledger.

*Mechanics:* multiple modules per app is ordinary Frappe — ERPNext ships more than twenty. A
DocType's `module` lives in its JSON and maps to a folder (`Apna Slot Core` →
`apna_slot/apna_slot_core/doctype/`), so both module folders and both `modules.txt` lines must exist
before the first DocType is created; moving a DocType between modules later means editing its JSON
and moving its folder. `hooks.py` fixtures select by doctype and export to `apna_slot/fixtures/` at
app level, so modules do not affect them. Only the module *names* are still open — Q-1 in
[PROGRESS.md](./PROGRESS.md), settled in step T-a.

### D-34 — Public venue reads go through `api.discovery`, not the permission query · *Settled*

Settles Q-1's successor, Q-2. `Venue`'s `permission_query_conditions` stays a **pure tenant
boundary** — `publisher in (…)`, and `1=0` for a non-member — exactly like every other tenant
doctype. It gains no `OR status = "Published"` clause, and `Venue` grants no read permission to the
`Guest` role. Everything a customer or a guest sees comes from `apna_slot/api/discovery.py`, whose
functions apply `status = "Published"` themselves and return a curated field list.

*Rejected:* one condition serving both paths — `publisher in (…) OR status = "Published"`, as
sketched in [phase-1-listing.md](./phase-1-listing.md) §2. It reads economically and costs three
things:

- The condition can then never be `1=0`, so the fail-closed property R3 exists to prove would hold
  for `Publisher` and not for `Venue` — the doctype where a leak actually matters.
- It needs `Guest` read on the Venue doctype, which opens `/api/v2/document/Venue` to arbitrary
  guest `fields` and `filters`: every field of a published venue, contact details included, and
  every field later phases add.
- A published venue is not a *tenant* of the reader. Tenancy and publication are two different
  questions, and sharing one expression means neither can change without disturbing the other.

*Accepted cost:* each discovery function repeats its `status = "Published"` filter. That is one
line in a module whose entire purpose is the public read path, and it makes 404-not-403 (Phase 5)
a property of the function rather than a side effect of a query condition.
