# Phase 2 — Pricing

**Goal:** a publisher can say "weekends cost more, and 18:00–23:00 costs more than that, and the
Christmas week costs the most" — and see the resulting price for any slot before saving.

> **Already delivered by [Phase T](./phase-t-tracer.md).** `PriceResolver`, constructed from one
> resource document and returning `base_price` with the label `Base Price`, already wired into the
> availability grid and into booking creation. **This phase replaces its body** with rule matching
> and priority resolution — the seam exists, so no caller changes. See
> [02-conventions.md](./02-conventions.md) §2 for the class shape; the module-level
> `resolve_slot_price(...)` named below remains as its thin public wrapper.

## In scope

`Resource Price Rule` child table, the resolver, the quote API, publisher pricing UI with a live
price calendar.

## Out of scope

Discounts, coupons, member rates, dynamic/surge pricing, taxes. All Phase 7.

---

## 1. `Resource Price Rule` (child of Bookable Resource)

| Fieldname | Fieldtype | Options | Notes |
|---|---|---|---|
| `rule_name` | Data | | **reqd**, e.g. "Weekend prime time"; shown on the booking breakdown |
| `is_active` | Check | | default `1` |
| `day_preset` | Select | `All days`\|`Weekdays`\|`Weekends`\|`Custom` | UI helper; sets the day checks |
| `monday` … `sunday` | Check | | seven fields. All unchecked ≡ all days |
| `start_time` | Time | | optional; band start, inclusive |
| `end_time` | Time | | optional; band end, **exclusive** |
| `valid_from` | Date | | optional |
| `valid_to` | Date | | optional |
| `price` | Currency | `currency` | **reqd**, > 0. Price for **one slot** |
| `priority` | Int | | default `0` → auto-computed from specificity on save |

> Seven `Check` fields rather than a nested multi-select: Frappe child tables cannot contain
> another child table, and seven booleans are directly usable in a query if rule matching ever
> needs to move into SQL.

### Validation (`bookable_resource.validate`)

- `start_time` and `end_time` are both set or both empty; same for `valid_from` / `valid_to`.
- `start_time < end_time`, with `end_time = 00:00:00` meaning end-of-day.
- A time band should align to the slot grid; if it does not, warn (`frappe.msgprint`) rather than
  block — a band of 18:30–23:00 on a 60-minute grid simply matches no slot start, and telling the
  publisher that is more useful than refusing the save.
- `price > 0`. Zero-price slots would model "free", which is not a supported product.
- Warn on an exactly-duplicated scope (same days, band and date range) at the same priority — the
  second rule is unreachable.

### Auto-priority

Computed on save when `priority == 0`:

```
priority = 0
        + 8  if valid_from == valid_to        (a single specific date)
        + 4  if valid_from/valid_to set       (a date range)
        + 2  if start_time/end_time set       (a time band)
        + 1  if the day set is a strict subset of all seven days
```

So a single-date rule (12) beats a season+band rule (6), which beats a weekend-band rule (3),
which beats a weekend rule (1), which beats `base_price`. A publisher who edits `priority`
manually keeps their value — the field is only auto-filled when left at 0.

---

## 2. The resolver — `apna_slot/pricing.py`

```python
def resolve_slot_price(resource: dict, slot_date: date, slot_start: time) -> tuple[Decimal, str]:
    """Return (price, rule_label) for one slot. rule_label is the rule_name, or 'Base Price'."""
```

Algorithm — deliberately dumb, deliberately explainable:

1. Take `resource.price_rules` where `is_active`.
2. Keep rules that match **all** of their own set conditions:
   - **day**: no day checked ⇒ matches; otherwise the weekday of `slot_date` must be checked.
   - **band**: unset ⇒ matches; otherwise `start_time <= slot_start < end_time`
     (with `end_time == 00:00` treated as 24:00). The **slot start** decides, not the slot end —
     a 22:00–23:00 slot under an 18:00–23:00 band matches, and there is no proration.
   - **dates**: unset ⇒ matches; otherwise `valid_from <= slot_date <= valid_to`, inclusive both
     ends.
3. Sort by `priority` desc, then `idx` asc. **First match wins.** No stacking (D-12).
4. No match ⇒ `(resource.base_price, "Base Price")`.

Rules:
- Pure function of its arguments — no DB access inside, so a day's grid resolves 24 prices from
  one already-loaded resource document.
- `Decimal` throughout; round once at the end with `frappe.utils.flt(value, precision)` using the
  venue currency's precision. Never accumulate floats.
- Weekday is derived from the **venue-local** `slot_date` (I-9). A UTC-derived weekday would price
  Saturday 00:30 in Dubai as a Friday.

```python
def quote(resource_name: str, requested_slots: list[dict]) -> dict:
    """Priced breakdown across one or many dates. The single source of money truth for
    the checkout preview and for Booking creation — Phase 3 calls this, it does not
    reimplement it.

    requested_slots: [{"date": "2026-09-12", "start_times": ["19:00:00", "20:00:00"]},
                      {"date": "2026-09-19", "start_times": ["19:00:00"]}]
    """
```

Each requested slot becomes one priced **line**, resolved against **its own date** — so a weekly
series prices every Saturday independently, and a line landing on a holiday rule costs what that
rule says while its siblings do not (I-6).

Returns:

```json
{
  "resource": "RES-00001",
  "currency": "AED",
  "lines": [
    {"date": "2026-09-12", "start_time": "19:00:00", "end_time": "20:00:00", "price": 250.0, "rule": "Weekend prime time"},
    {"date": "2026-09-12", "start_time": "20:00:00", "end_time": "21:00:00", "price": 250.0, "rule": "Weekend prime time"},
    {"date": "2026-09-19", "start_time": "19:00:00", "end_time": "20:00:00", "price": 300.0, "rule": "National holiday"}
  ],
  "line_count": 3,
  "date_count": 2,
  "subtotal": 800.0,
  "total_amount": 800.0
}
```

Resource and rules are loaded **once** for the whole quote; a 6-date quote costs the same queries
as a 1-date quote.

`subtotal` and `total_amount` are equal in Phase 2–6; the split exists so taxes and discounts land
later without changing the field the UI reads.

---

## 3. APIs

| Method | Guest? | Params | Notes |
|---|---|---|---|
| `apna_slot.api.pricing.get_quote` | yes | `resource`, `slots[]` (the `{date, start_times[]}` list) | The payload above. Validates that slots are on the grid, that no `(date, start_time)` repeats, that each date is within `max_slots_per_booking` and the request within `max_dates_per_booking`, and that the resource's venue is `Published`. **Adjacency is not required** (D-28). Does **not** check availability — that is Phase 3. |
| `apna_slot.api.pricing.preview_calendar` | no | `resource`, `from_date`, `to_date` | Publisher-only. Per-day `{date, min_price, max_price, distinct_rules[]}` for the pricing calendar. Capped at 92 days. |
| `apna_slot.api.pricing.preview_day` | no | `resource`, `date` | Publisher-only. Every slot for one day with its resolved price and the rule name that won. |

`get_quote` is guest-allowed so an anonymous browser sees prices; it must therefore never leak
anything but the resource's public pricing.

---

## 4. Frontend

Route: `/apnaslot/manage/venues/:name/resources/:resource` → **Pricing** tab.

- **Base price** at the top: one `FormControl` with the currency symbol as `#prefix`.
- **Rules list**: `List` / `ListRow`, ordered by effective priority so the publisher reads them in
  the order the resolver applies them, each row showing scope as a human sentence — *"Sat, Sun ·
  18:00–23:00 · all year · AED 250"* — with the computed priority as a `Badge` and a drag handle to
  override ordering.
- **Rule editor**: `Dialog` with the `day_preset` `Select` driving seven checkboxes, two optional
  `FormControl type="time"` inputs, an optional date range, and the price.
- **Live preview** — the point of the whole screen. A month calendar (`preview_calendar`) showing
  each day's price range, and clicking a day opens the hour-by-hour breakdown (`preview_day`) with
  the winning rule named on each slot. Rule edits re-query the preview before saving, so a
  publisher never discovers a mis-scoped rule through a customer paying the wrong price.
- A "no rule matches" hint when a rule is unreachable (shadowed by a higher-priority rule with a
  superset scope) — computed client-side from the preview, shown as a warning `Badge` on the row.

---

## 5. Acceptance criteria

1. With no rules, every slot prices at `base_price` with rule label `Base Price`.
2. A weekend rule prices Saturday and Sunday slots at its price and leaves weekdays at base.
3. A weekend rule plus a weekend-evening band: the 19:00 slot takes the band price, the 10:00 slot
   takes the weekend price, a Tuesday 19:00 slot takes base.
4. A single-date holiday rule beats both, on that date only.
5. Priorities auto-compute to 1 / 3 / 12 for those three rules respectively.
6. A manually set priority survives save and overrides the auto value.
7. `get_quote` for two slots returns two lines whose prices sum to `total_amount`, whether or not
   they are adjacent.
8. `get_quote` across six Saturdays returns six lines, each priced for its own date, and a total
   equal to their sum.
9. `get_quote` refuses off-grid start times, a repeated `(date, start_time)`, more than
   `max_slots_per_booking` on one date, more than `max_dates_per_booking` overall, and resources
   whose venue is not `Published`.
10. A band of 18:00–23:00 matches the 22:00 slot (start-time rule) and not the 23:00 slot.
11. Editing a rule does not change the stored amount of any existing booking (proved in Phase 3
    once bookings exist; asserted here against a fixture booking).

## 6. Tests — `apna_slot/tests/test_phase2.py`

| Test | Asserts |
|---|---|
| `test_base_price_fallback` | no rules ⇒ base, label `Base Price` |
| `test_weekend_rule_matches_weekend_only` | Sat/Sun vs Mon |
| `test_time_band_uses_slot_start` | 22:00 in an 18:00–23:00 band matches; 23:00 does not |
| `test_end_time_midnight_is_end_of_day` | 23:00 slot matches an 18:00–00:00 band |
| `test_date_range_inclusive_both_ends` | `valid_from` and `valid_to` days both match |
| `test_specific_date_beats_range_beats_band` | full precedence ladder |
| `test_auto_priority_scores` | 1 / 3 / 12 |
| `test_manual_priority_respected` | non-zero priority not overwritten |
| `test_equal_priority_breaks_by_idx` | earlier row wins |
| `test_inactive_rule_ignored` | falls through |
| `test_weekday_derived_from_venue_local_date` | Dubai Saturday 00:30 prices as Saturday |
| `test_quote_sums_and_rounds_once` | subtotal == sum, currency precision honoured |
| `test_quote_allows_non_adjacent_slots` | 10:00 + 19:00 on one date quotes two lines |
| `test_quote_across_dates_prices_per_line_date` | six Saturdays, holiday line differs |
| `test_quote_rejects_duplicate_date_time` | raises |
| `test_quote_rejects_over_max_dates` | raises |
| `test_quote_query_budget_flat_across_dates` | 6 dates == 1 date |
| `test_quote_rejects_off_grid_start` | 19:30 on a 60-minute grid raises |
| `test_quote_rejects_over_max_slots` | raises |
| `test_price_edit_does_not_alter_existing_booking` | snapshot holds (I-6) |
