# Phase 1 — Listing

**Goal:** a publisher can create a venue, add bookable resources with weekly opening hours, write
rules, tag amenities, declare closures, and publish it — with everything a customer will later
need to see already captured.

> **Already delivered by [Phase T](./phase-t-tracer.md).** `Venue`, `Bookable Resource` and
> `Resource Schedule Row` at minimum field set (name, publisher, slug, status, locale, schedule,
> `base_price`, the booking-window fields), publish, and a bare venue list plus create form.
> **This phase adds:** description, images, amenities and rules; the full policy block including
> `free_cancellation_hours`; `activity_type` and resource images; `Resource Closure`;
> `duplicate_resource`; and the real publisher surface — the venue wizard, tabbed detail, the
> schedule builder with its live slot preview, and the publish-readiness banner.

## In scope

`Venue` (+ image / amenity / rule children), `Bookable Resource` (+ schedule rows),
`Resource Closure`, publisher CRUD screens, publish/unpublish, slug generation.

## Out of scope

Pricing beyond `base_price` (Phase 2). Availability computation, bookings, customer-facing venue
pages (Phases 3 and 5).

---

## 1. DocTypes

### `Venue` — naming `VEN-.#####`

| Fieldname | Fieldtype | Options | Notes |
|---|---|---|---|
| `venue_name` | Data | | **reqd** |
| `publisher` | Link | Publisher | **reqd**, read-only after insert |
| `slug` | Data | | unique, auto-generated, read-only; used at `/apnaslot/venues/:slug` |
| `status` | Select | `Draft`\|`Published`\|`Unlisted`\|`Suspended`\|`Under Review` | default `Draft`. `Under Review` is reserved (D-7); no code sets it. `Suspended` is admin-only. |
| `description` | Text Editor | | rich text (D-15) |
| `cover_image` | Attach Image | | |
| `images` | Table | Venue Image | gallery |
| **Location** | | | |
| `address_line_1` | Data | | **reqd** |
| `address_line_2` | Data | | |
| `city` | Data | | **reqd**, indexed — the primary search filter |
| `state` | Data | | |
| `country` | Link | Country | **reqd** |
| `postal_code` | Data | | |
| `latitude` | Float | | precision 8; captured, unused in Phase 1–6 (no maps, D-20) |
| `longitude` | Float | | precision 8; same |
| **Locale** | | | |
| `timezone` | Data | | **reqd**, defaults from publisher, IANA validated |
| `currency` | Link | Currency | **reqd**, defaults from publisher; read-only once any booking exists |
| **Contact** | | | |
| `contact_phone` | Data | Phone | |
| `contact_email` | Data | Email | |
| **Content** | | | |
| `amenities` | Table MultiSelect | Venue Amenity | |
| `rules` | Table | Venue Rule | shown at checkout as an acknowledgement list |
| **Policy** | | | |
| `max_advance_days` | Int | | default `60`, 1–365 |
| `min_lead_minutes` | Int | | default `60`, 0–10080 |
| `free_cancellation_hours` | Int | | default `24`, 0–720 (D-13) |
| `cancellation_policy_text` | Small Text | | shown at checkout |
| `published_on` | Datetime | | set when status first becomes `Published` |

**Child doctypes**

`Venue Image`: `image` (Attach Image, reqd), `caption` (Data). Reused by `Bookable Resource`.
`Venue Amenity` (Table MultiSelect): `amenity` (Link Amenity, reqd).
`Venue Rule`: `rule_text` (Small Text, reqd, `in_list_view`).

**Controller `venue.py`**

- `autoname`/`before_insert`: `slug = frappe.scrub(venue_name).replace("_", "-")`, de-duplicated
  with a numeric suffix. Immutable afterwards — changing a live URL breaks shared links.
- `validate`: IANA timezone; `publisher` is one of `get_user_publishers()` unless System Manager;
  policy fields within range; `currency` change blocked when any Booking references the venue.
- `before_save`: block `status = "Published"` unless the venue has **at least one Active
  `Bookable Resource` with a complete weekly schedule and a `base_price` > 0**. A published venue
  that cannot be booked is worse than an unpublished one — the error names the missing piece.
- `on_update`: stamp `published_on` on the first publish.
- `on_trash`: refuse if any Booking references the venue; suggest `Unlisted` instead.

### `Bookable Resource` — naming `RES-.#####`

| Fieldname | Fieldtype | Options | Notes |
|---|---|---|---|
| `resource_name` | Data | | **reqd**, e.g. "Turf A (5-a-side)" |
| `venue` | Link | Venue | **reqd**, read-only after insert |
| `publisher` | Link | Publisher | fetched from venue, read-only, hidden — exists so permission queries never need a join |
| `activity_type` | Link | Activity Type | **reqd** |
| `status` | Select | `Active`\|`Inactive` | default `Active`; `Inactive` hides it from availability but keeps existing bookings |
| `description` | Small Text | | |
| `images` | Table | Venue Image | |
| **Slotting** | | | |
| `slot_duration_minutes` | Select | `30`\|`45`\|`60`\|`90`\|`120` | default `60`; read-only once any Booking Slot exists for this resource |
| `max_slots_per_booking` | Int | | default `4`, 1–12 — max slots **per date** in one booking (I-3) |
| `max_dates_per_booking` | Int | | default `8`, 1–26 — max distinct dates in one booking; caps the weekly-series length (D-28) |
| `capacity` | Int | | default `1`, **hidden, read-only** — reserved (D-14); no code reads it |
| `requires_approval` | Check | | default `0`, **hidden** — reserved (D-2) |
| **Pricing** | | | |
| `base_price` | Currency | `currency` | **reqd**, > 0. Price for one slot when no rule matches |
| `currency` | Data | | fetched from venue, read-only, hidden — the `options` target for money fields |
| `price_rules` | Table | Resource Price Rule | **Phase 2**; the field ships empty in Phase 1 |
| **Schedule** | | | |
| `weekly_schedule` | Table | Resource Schedule Row | **reqd**, min 1 row |

**`Resource Schedule Row` (child)**

| Fieldname | Fieldtype | Options | Notes |
|---|---|---|---|
| `day_of_week` | Select | `Monday`…`Sunday` | **reqd**, `in_list_view` |
| `opens_at` | Time | | **reqd** |
| `closes_at` | Time | | **reqd**; `00:00:00` means end-of-day (24:00) |

Multiple rows per day are allowed and express split shifts (06:00–12:00 and 16:00–23:00).

**Controller `bookable_resource.py`**

- `validate`:
  - `opens_at < closes_at`, unless `closes_at == 00:00:00` (end-of-day, per the domain model).
  - No two rows for the same `day_of_week` may overlap.
  - Each row's span must be an exact multiple of `slot_duration_minutes`; otherwise raise naming
    the offending row and the remainder — a 06:00–12:30 window with 60-minute slots is a
    configuration error, not something to silently truncate.
  - `slot_duration_minutes` change blocked once any `Booking Slot` row exists (it would
    re-partition a grid that bookings already sit on).
- `before_save`: fetch `publisher` and `currency` from the venue.
- `on_trash`: refuse if any Booking references it.

### `Resource Closure` — naming `CLS-.#####`

| Fieldname | Fieldtype | Options | Notes |
|---|---|---|---|
| `venue` | Link | Venue | **reqd** |
| `resource` | Link | Bookable Resource | optional — **blank means the whole venue** |
| `publisher` | Link | Publisher | fetched, hidden |
| `from_date` | Date | | **reqd** |
| `to_date` | Date | | **reqd**, ≥ `from_date` |
| `whole_day` | Check | | default `1` |
| `from_time` | Time | | required when `whole_day = 0` |
| `to_time` | Time | | required when `whole_day = 0`, > `from_time` |
| `reason` | Small Text | | shown to the customer as "Unavailable — maintenance" |

**Controller**: `resource` must belong to `venue`; on save, warn (do not block) when the closure
overlaps existing `Confirmed` bookings, and list them — the publisher then cancels those
explicitly through the Phase 6 flow. Closures never auto-cancel bookings.

---

## 2. Permissions

Extend `hooks.py` and `permissions.py`:

```python
permission_query_conditions = {
    "Publisher": "apna_slot.permissions.publisher_query",
    "Venue": "apna_slot.permissions.tenant_query",
    "Bookable Resource": "apna_slot.permissions.tenant_query",
    "Resource Closure": "apna_slot.permissions.tenant_query",
}
```

`tenant_query(user, doctype)` returns `` `tab{doctype}`.publisher in (…) `` — which is why
`publisher` is denormalised onto `Bookable Resource` and `Resource Closure`. For **Venue** the
condition is `OR status = 'Published'` when the doctype is read by a customer or guest, so the
public listing works through the same code path as the publisher listing.

`has_permission`: `Staff` members get read-only on Venue and Bookable Resource; `Owner` and
`Manager` get write.

---

## 3. APIs

Venue, Bookable Resource and Resource Closure CRUD use the standard `frappe.client` REST layer via
`useDoc` / `useList`. Custom endpoints only where there is logic:

| Method | Params | Notes |
|---|---|---|
| `apna_slot.api.venue.publish` | `venue` | Runs the publishability checks and sets `Published`; returns `{"status", "missing": [...]}` so the UI can list what's missing instead of just failing |
| `apna_slot.api.venue.unpublish` | `venue` | Sets `Unlisted`. Existing bookings are untouched |
| `apna_slot.api.venue.duplicate_resource` | `resource`, `new_name` | Copies schedule + pricing — a venue with six identical courts is the common case |
| `apna_slot.api.venue.get_taxonomies` | — | `{activity_types: [...], amenities: [...]}`, guest-allowed, cached |

---

## 4. Frontend

| Route | Screen |
|---|---|
| `/apnaslot/manage/venues` | venue list, status badge, resource count, "Add Venue" |
| `/apnaslot/manage/venues/new` | creation wizard: basics → location → content → policy |
| `/apnaslot/manage/venues/:name` | tabbed detail: Overview · Resources · Rules & Amenities · Policy · Photos |
| `/apnaslot/manage/venues/:name/resources/:resource` | resource editor incl. the schedule builder |
| `/apnaslot/manage/closures` | closure list + create dialog |

**Components (frappe-ui):** `List` / `ListRow` for the venue and closure lists; `Tabs` for venue
detail; `FormControl` throughout with `label`/`description`/`error`/`required`;
`Combobox` for activity type and country; `MultiSelect` for amenities; `Editor` from
`frappe-ui/editor` for the description; `FileUploader` + a grid for photos; `Badge` for status;
`Dialog` for closure creation; `dialog.confirm` before unpublish; `toast` on save.

**Schedule builder.** Seven day rows, each with a toggle and one or more time ranges (`+ Add
hours` for split shifts), plus a "Copy Monday to all weekdays" action. Below it, a live preview
strip renders the slots the current configuration generates for the selected day — the publisher
sees `06:00 · 07:00 · 08:00 …` and immediately understands the multiple-of-slot-duration rule
instead of meeting it as a validation error.

**Publish affordance.** A persistent banner on an unpublished venue lists exactly what is missing
("Add at least one resource", "Turf A has no opening hours", "Turf B has no base price"), each
item deep-linking to the field. The Publish button is enabled only when the list is empty.

---

## 5. Acceptance criteria

1. A publisher creates a venue, adds one resource with Mon–Sun 06:00–23:00 hours at 60 minutes and
   a base price, and publishes it. `published_on` is stamped and `slug` is set.
2. Publishing is refused, with a specific message, when there is no resource / no schedule / no
   base price.
3. A schedule row of 06:00–12:30 with 60-minute slots is refused, naming the row.
4. Overlapping rows for the same weekday are refused.
5. `closes_at = 00:00` is accepted and treated as end-of-day; `closes_at < opens_at` otherwise is
   refused.
6. `slot_duration_minutes` cannot be changed once a Booking Slot exists (verified in Phase 3).
6b. `max_dates_per_booking` above 1 makes the venue bookable as a series; setting it to 1 restricts
    the venue to single-date bookings without any other change.
7. Publisher B cannot read, list, or edit Publisher A's venue, resource or closure — via REST or
   through the SPA.
8. A guest listing venues sees `Published` venues only, and never a `Draft` or `Unlisted` one.
9. A venue-level closure (blank `resource`) applies to every resource at that venue.
10. Deleting a venue with bookings is refused and suggests `Unlisted`.

## 6. Tests — `apna_slot/tests/test_phase1.py`

| Test | Asserts |
|---|---|
| `test_slug_generated_and_unique` | second same-named venue gets a suffix |
| `test_slug_immutable_after_insert` | rename does not change slug |
| `test_publish_requires_bookable_resource` | `ValidationError` listing what's missing |
| `test_publish_stamps_published_on` | timestamp set once, not on republish |
| `test_schedule_must_divide_evenly` | 06:00–12:30 @ 60min raises |
| `test_schedule_overlap_rejected` | two overlapping Monday rows raise |
| `test_midnight_close_accepted` | `closes_at = 00:00` valid |
| `test_reverse_time_rejected` | 22:00–06:00 raises |
| `test_resource_inherits_publisher_and_currency` | fetched from venue |
| `test_venue_currency_locked_after_booking` | change raises (Phase 3 fixture) |
| `test_closure_resource_must_match_venue` | cross-venue resource raises |
| `test_cross_tenant_venue_invisible` | list and get both denied |
| `test_guest_sees_only_published` | draft/unlisted absent |
| `test_trash_venue_with_bookings_refused` | raises, message suggests Unlisted |
