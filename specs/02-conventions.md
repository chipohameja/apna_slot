# Code Conventions

[CLAUDE.md](../CLAUDE.md) states the rules. This document applies them to *this* codebase, and
resolves the three places where a rule and the design meet awkwardly. Read it before writing code;
the phase documents assume it.

---

## 1. Module layout — the 15-file rule

CLAUDE.md caps a folder at ~15 files. The plan has **18 DocTypes**, and Frappe requires every
DocType of a module to live in `<app>/<module>/doctype/`. One module therefore cannot hold them.

**Resolution: two modules.**

```
apna_slot/
├─ apna_slot_core/doctype/          # 12 doctypes — who lists what
│  publisher · publisher_member · activity_type · amenity
│  venue · venue_image · venue_amenity · venue_rule
│  bookable_resource · resource_schedule_row · resource_price_rule · resource_closure
└─ apna_slot_booking/doctype/       # 6 doctypes — who booked what, and who paid
   booking · booking_line · booking_slot
   payment_transaction · refund · refund_line
```

`modules.txt` lists both: `Apna Slot Core` and `Apna Slot Booking`. The split is not cosmetic — it
is the seam between *inventory* and *ledger*, and it is the same seam the permission model uses
(`tenant_query` for core, `tenant_query` + customer clause for booking).

Everything else stays flat and small:

```
apna_slot/
├─ api/            auth · publisher · venue · pricing · availability · booking · payment · discovery   (8)
├─ gateways/       base · mock · registry                                                              (3)
├─ utils/          timezone · slots · money                                                            (3)
├─ tests/          one module per phase + fixtures                                                     (9)
├─ patches/v1_0/
├─ availability.py · pricing.py · booking_engine.py · permissions.py · notifications.py
├─ jobs.py · constants.py · exceptions.py
```

Frontend mirrors it: no folder under `frontend/src/` exceeds 15 files. When `pages/` approaches the
cap, split by area (`pages/manage/`, `pages/book/`), not by adding a sixteenth file.

---

## 2. Object orientation — where classes earn their place

CLAUDE.md: *"Write object oriented code as much as possible."* Frappe already gives one class per
DocType. The judgement call is the engine modules, which the phase docs sketch as free functions.

**Rule: state gets a class; a pure mapping stays a function.**

| Concern | Shape | Why |
|---|---|---|
| DocType controllers | `class Venue(Document)` | Frappe's own contract |
| Price resolution | `class PriceResolver` — constructed from one resource document, `price_for(slot_date, slot_start)` | The "load the resource once, resolve N slots" rule from Phase 2 becomes *structural* instead of a convention a caller can forget |
| Availability | `class AvailabilityGrid` — holds resource, closures and ledger for a date span; `for_date()`, `for_dates()` | The batched-query budget (Phase 3 §3) is enforced by the constructor, not by discipline |
| Booking creation | `class BookingRequest` — validates shape, prices, claims, rolls back; `submit()` | The critical section is one object with one entry point, so the transaction boundary is visible in one place |
| Gateways | `class PaymentGateway(ABC)` → `MockGateway` | The whole point of D-16 |
| Cancellation | `class CancellationRequest` with `CustomerPolicy` / `VenuePolicy` strategies | The two paths differ only in their window check; a strategy makes that the *only* difference |
| `expand_weekly_series`, `slot_range`, `to_utc` | free functions in `utils/` | Pure input→output, no state, no polymorphism to gain |

The module-level functions named in the phase docs (`resolve_slot_price`, `get_day_grid`,
`create_booking`, …) remain as **thin public wrappers** over these classes, so the API signatures
those documents publish do not change:

```python
def resolve_slot_price(resource, slot_date, slot_start):
    return PriceResolver(resource).price_for(slot_date, slot_start)
```

Do **not** create a class whose only method is `run()` and whose only field is its argument. That
is a function wearing a costume.

---

## 3. Function and file size

- **Functions ≤ 10 lines** of body. The tools that get you there, in order: early return over
  nested `if`; extract a named predicate (`self._is_within_window(line)`) instead of an inline
  boolean expression spanning three lines; extract each validation into its own method and have
  `validate()` call them in sequence.
- Frappe controllers naturally become `def validate(self): self._check_timezone(); self._check_policy_ranges(); …`. That reads as a table of contents, which is the goal.
- **Files 100–300 lines.** When `booking_engine.py` approaches 300, the split is
  `booking_engine.py` (the request object) / `ledger.py` (claim and release) — by responsibility,
  never by line count alone. A 60-line file is fine; a 60-line file that exists only to hold one
  constant is not.

---

## 4. Naming — no abbreviations

The phase documents were drafted with a few shorthand names. These are the corrections; the code is
authoritative.

| Do not write | Write |
|---|---|
| `txn` | `transaction` |
| `res`, `rsrc` | `resource` |
| `pub` | `publisher` |
| `qty`, `amt` | `quantity`, `amount` |
| `dt`, `ts` | `doctype`, `timestamp` |

Kept deliberately, because they are the domain's own vocabulary and expanding them makes the code
*less* clear: `utc` (`start_utc`), `idx`, `id`, `url`, `api`, `dst`, `hmac`, `iana`, `qb`
(`frappe.qb` is Frappe's own name). Naming record ids `PUB-` / `VEN-` / `RES-` / `BKG-` / `PAY-` /
`REF-` / `CLS-` is a user-facing convention, not code naming, and stands.

---

## 5. Reuse before writing

In descending order of preference:

1. **Frappe standard API.** `frappe.get_doc`, `frappe.get_all`, `frappe.qb`, `frappe.sendmail`,
   Email Template, the rate limiter, `frappe.client` REST for plain CRUD. Custom endpoints only
   where there is logic (this is already the rule in Phases 1 and 5).
2. **frappe-ui components.** `List`/`ListRow`, `FormControl`, `Dialog`, `Tabs`, `Badge`, `Button`,
   `toast`, `useCall`/`useList`/`useDoc`. Never a hand-rolled `<button class="bg-…">`, never a
   bespoke fetch wrapper.
3. **Espresso design tokens.** `bg-surface-*`, `text-ink-*`, `border-outline-*`. No hex values, no
   raw Tailwind palette colours (`bg-gray-100`) — they break dark mode, which is an acceptance
   criterion in every frontend phase.
4. **Our own seams.** Phase 3 calls Phase 2's `quote()`; it does not reimplement pricing. Phase 6
   calls `release_line`; it does not delete ledger rows itself. If two phases need the same logic,
   the later one calls the earlier one's function or the function moves to `utils/`.

Write SQL only through `frappe.qb`. The single exception in the whole plan is the unique-index
patch, which is DDL that no ORM expresses.

---

## 6. Comments and documentation

CLAUDE.md asks for low verbosity. Applied:

- A one-line docstring on a public function whose signature does not already say what it does.
  No `:param:` blocks, no restating the type hints.
- Inline comments only for a decision a reader would otherwise undo — and they cite the decision:
  `# fold=0: ambiguous local hour resolves to the first occurrence (D-9)`.
- No commented-out code, no `# TODO` without a phase reference, no file-header banners.
- The *explanation* of a change belongs in the commit message (see
  [04-workflow.md](./04-workflow.md)); the *rationale* for a design belongs in
  [01-decisions.md](./01-decisions.md). Neither belongs in a comment block.

---

## 7. Error handling

- Domain errors are named classes in `apna_slot/exceptions.py`: `SlotUnavailableError`,
  `HoldExpiredError`, `CancellationWindowClosedError`, `TenantAccessError`. Each carries structured
  data the UI needs (`conflicting_lines`, `deadline_utc`), not just a string.
- User-facing messages name the specific thing and the next action — the standard the phase docs
  already set: *"12 Sep 19:00 can no longer be cancelled online … Your other 5 dates can still be
  cancelled."* Never "An error occurred".
- Never leak existence across a tenant boundary: unpublished venue ⇒ 404, not 403 (Phase 5).
- `ignore_permissions=True` appears only inside a named function that is *about* privilege
  (`_claim_ledger_rows`), never as a blanket flag on a request path.
