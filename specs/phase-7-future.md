# Phase 7 — Deferred: what was left out and what it costs

Nothing here is built. Each entry records what was deferred, the decision that deferred it, what
unblocking it actually requires, and what would break if it were bolted on carelessly.

Read this before saying yes to any of these — several are cheap, and two are structural.

---

## Real payment gateway (Razorpay / Stripe)

**Deferred by:** D-16. **Cost: low — this is what Phase 4 was shaped for.**

New class implementing `PaymentGateway` (`create_checkout`, `verify_callback`, `refund`), API keys
in site config, `apna_slot_payment_gateway` switched off `Mock`, and the gateway's webhook URL
pointed at `apna_slot.api.payment.callback`.

Real work beyond the class: webhook signature verification against the vendor's scheme (the mock's
HMAC step is a placeholder, not the algorithm), webhook retry/ordering (a `succeeded` can arrive
before your redirect handler runs), and the `authorized` vs `captured` distinction if the vendor
separates them. `api.payment.simulate` must be unregistered outside the Mock gateway — shipping it
against a live gateway would be a critical vulnerability.

## Payouts and settlement

**Deferred by:** D-23. **Cost: high — needs a real gateway first.**

Commission and payout amounts are already snapshotted per booking (I-10). Missing: a settlement
period model, a `Payout` document aggregating bookings per publisher per period, publisher bank
details with proper handling as sensitive data, reconciliation against gateway settlement reports,
and refund clawback from an already-paid-out booking. That last one is the hard part and needs a
negative-adjustment concept before any money moves.

## Request-to-book (approval required)

**Deferred by:** D-2. **Cost: medium.**

`Bookable Resource.requires_approval` already exists (hidden, unread). Needs: two new booking
states (`Awaiting Approval`, `Rejected`), gateway authorise-then-capture rather than immediate
capture, a publisher response deadline with its own expiry job, publisher notification and an
approval UI, and a decision about whether the slot is held during the wait (it must be, which means
a second, much longer hold with different economics).

## Per-slot capacity > 1

**Deferred by:** D-14. **Cost: high — structural.**

This is the one deferral that invalidates a core invariant. `Booking Slot`'s unique index on
`(resource, slot_date, start_time)` **is** I-1; capacity > 1 replaces it with a counting query
under a lock, which is exactly the design rejected in D-17. Doing it properly means either a
per-slot counter row updated with `SELECT … FOR UPDATE`, or N pre-allocated "seat" rows keeping a
unique index on `(resource, date, start_time, seat_no)`. The seat approach preserves the guarantee
and is the recommended path if this is ever needed. Do not solve it with an application-level
count-then-insert.

## Buffer time between bookings

**Deferred by:** D-14. **Cost: medium.**

Currently expressible by choosing a longer slot duration. A true buffer breaks the clean grid: the
slot after a booked slot becomes conditionally unavailable, so availability stops being a pure
function of the ledger and becomes ledger-plus-neighbours. Availability generation and the
adjacency rules both need rework.

## Partial deposits

**Deferred by:** D-6. **Cost: medium.**

Needs `amount_paid` vs `amount_due` on Booking, a second payment event at the venue (or a second
online payment), and a policy for what happens when the balance is never paid. Refunds are already
many-per-booking (D-31), but they refund whole lines at their booked price — a deposit needs
refunds of *arbitrary* amounts, which is the part Phase 6 does not do.

## Tiered cancellation refunds (100 / 50 / 0%)

**Deferred by:** D-13. **Cost: low.**

A child table of `{hours_before, refund_percent}` on the Venue, resolved by the same highest-match
approach as pricing. The Refund document already supports covering a subset of lines (D-31), so the
remaining work is a percentage per line rather than its full price — computed and displayed before
the customer confirms.

## Rescheduling (moving a line to another slot)

**Not previously discussed.** **Cost: medium.**

The naive version — cancel and rebook — is already possible by hand and is the honest Phase 7
answer. A real reschedule must atomically claim the new slot *before* releasing the old one, or a
customer moving a booking can lose it to someone else mid-move. That is a second critical section
needing the same care as D-17. With lines (D-28) the unit of rescheduling is obvious — one line
moves, its siblings do not — which makes this materially easier than it would have been under the
single-date model.

## SMS / WhatsApp notifications

**Deferred by:** D-19. **Cost: low, plus money.**

The Phase 6 triggers are already channel-agnostic. Needs a vendor account, a phone verification
flow (a booking's phone is currently unverified free text), and template approval for WhatsApp.

## Cross-venue cart

**Deferred by:** D-28. **Cost: high — structural.**

A booking is one resource, hence one venue, hence one currency, timezone, publisher, commission rate
and cancellation policy — all snapshotted onto the record. A cart spanning venues needs a
`Booking Group` above `Booking`, payment split across publishers (which needs real gateway support
for split settlement), and a checkout that presents two currencies and two cancellation policies
without confusing anyone. Multi-date within one resource (D-28) already covers the common repeat
case; this is a genuinely different product surface.

## Season passes / memberships

**Not previously discussed.** **Cost: medium.**

`max_dates_per_booking` caps a booking at 8 dates by default. "Every Saturday for a year" is not a
longer booking — it is a subscription with recurring billing, pro-rata cancellation and a
materialisation policy for slots months out. Do not solve it by raising the cap: a 52-line booking
holds a year of inventory against a single payment and a single hold.

## Stored recurrence rules (RRULE)

**Deferred by:** D-30. **Cost: medium, and mostly conceptual.**

Recurrence is currently expanded to concrete lines at booking time. Storing the rule instead means
answering: how far ahead does it materialise, what happens when a date inside the rule is closed,
what does the publisher's calendar show for an unmaterialised date, and what happens when the rule
is edited after three weeks have been played. Only worth it alongside memberships, which need it.

## Multi-currency reporting / base currency

**Deferred by:** D-10. **Cost: low, and additive.**

Add `base_currency`, `exchange_rate` and `base_amount` to Booking, snapshot the rate at
confirmation, and backfill historical rows with a dated rate. Never convert at read time — a
report whose totals change with today's FX rate is not a report.

## Reviews, ratings, favourites, recommendations

**Not previously discussed.** **Cost: medium each.** All are additive and none touch the booking
core. Reviews need a "only customers with a `Completed` booking may review" gate, which the current
model supports directly.

## Maps and geo search

**Deferred by:** D-20. **Cost: medium, plus per-load billing.**

`Venue.latitude` / `longitude` already exist and are captured. Needs a Maps provider key, a
geocoding step at venue save, and a radius filter (`ST_Distance_Sphere`, or a bounding box for
simplicity). The bounding box is enough at any scale this app will see for a long time.

## Search at scale

**Not previously discussed.** **Cost: low until it isn't.**

Phase 5 uses `LIKE` and per-venue aggregates. That holds to a few thousand venues. Beyond that:
denormalise a `venue_search` table maintained on venue/resource save, or move to a real index. The
`available_on` filter is the first thing that will hurt.

## Waitlists

**Not previously discussed.** **Cost: medium.**

"Tell me if this slot frees up" is a natural fit for the release paths — every `release_booking`
call is already the exact hook a waitlist would fire from. Needs notification fan-out, a fairness
rule, and a short exclusive claim window for the notified customer.
