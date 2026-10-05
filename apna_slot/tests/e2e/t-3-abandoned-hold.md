# Journey T-3 — an abandoned hold expires

A hold the customer walks away from is released by `expire_pending_bookings` alone, per
[03-testing.md](../../../specs/03-testing.md) §4. This is the one journey that waits on real time:
the 10-minute hold plus at most one 2-minute sweep. The unit tests move `hold_expires_at` instead.

Needs `bench schedule` and a worker running, and the scheduler enabled for the site
(`bench --site apnaslot.localhost scheduler status`).

| # | Step | Assertion |
|---|---|---|
| 1 | As a customer, book a free slot and press **Pay** | `/apnaslot/pay/:token` with a countdown under 10:00 |
| 2 | Press **Abandon** | lands on `/apnaslot/`; the booking is `Pending Payment` with one ledger row; note `hold_expires_at` |
| 3 | Reopen the same `/pay/:token` | "This payment is already abandoned." and no buttons |
| 4 | Before `hold_expires_at`, read the grid from a second session | the slot reads **Booked** — nothing but the timer may free it |
| 5 | Wait for the first `*/2` tick after `hold_expires_at`, then reload the grid | the slot reads available again |
| 6 | Open My Bookings as the customer | the booking's badge reads `Expired` |
| 7 | Query the ledger | zero `Booking Slot` rows for that booking |

```sql
select name, status, hold_expires_at, utc_timestamp() from tabBooking where name = '<booking>';
select count(*) from `tabBooking Slot` where booking = '<booking>';
```

Finish with the checks every journey runs — dark, 375px, console — on My Bookings.
