# Journey T-2 — two customers, one slot

Two isolated browser sessions race for one slot through the real grid, per
[03-testing.md](../../../specs/03-testing.md) §4. B's grid is loaded **before** A takes the slot, so
B clicks a button that still reads available — the refusal comes from the ledger, not the UI.

Needs a published venue with free slots tomorrow (journey T-1 steps 1–9 leave one). Salt the emails
per run; the site keeps every earlier walk.

```bash
agent-browser --session apnaslot-a open http://apnaslot.localhost:8000/apnaslot/venues/<slug>
agent-browser --session apnaslot-b open http://apnaslot.localhost:8000/apnaslot/venues/<slug>
```

| # | Step | Assertion |
|---|---|---|
| 1 | In both sessions, sign up a customer (A, B) and open the venue page | both grids show 20:00 available |
| 2 | A clicks 20:00 | A lands on `/apnaslot/checkout/:booking`, `Pending Payment` |
| 3 | B, without reloading, clicks its stale 20:00 button | B stays on the venue page and reads "20:00 on *d Mon* is no longer available. Pick another slot." |
| 4 | Read B's grid | it refreshed itself: 20:00 reads **Booked** and is disabled |
| 5 | From B, `POST apna_slot.api.booking.create` for the same slot | HTTP **409**, the same message |
| 6 | Query the ledger for that resource and date | exactly one `Booking Slot` row at 20:00, owned by A's booking; B has no booking |

```sql
select s.start_time, s.booking, b.customer, b.status
from `tabBooking Slot` s join tabBooking b on b.name = s.booking
where s.resource = '<resource>' and s.slot_date = '<tomorrow>';
```

Finish with the checks every journey runs — dark, 375px, console — on B's grid.
