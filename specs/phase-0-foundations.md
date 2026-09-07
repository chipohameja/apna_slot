# Phase 0 — Foundations

**Goal:** a running SPA at `/apnaslot` where a user can sign up, log in, create a Publisher
business, and invite a teammate — with tenant isolation enforced at the database query level from
the very first record.

> **Already delivered by [Phase T](./phase-t-tracer.md).** `Publisher` + `Publisher Member` at
> minimum field set; `permissions.py` with `get_user_publishers`, `tenant_query` and the
> fail-closed `1=0` behaviour; `api.auth.sign_up` and `get_session_user`;
> `api.publisher.create_publisher`; the frappe-ui SPA scaffold with login, signup and the router
> guards. **This phase adds:** the `Activity Type` and `Amenity` taxonomies and their fixtures, the
> remaining Publisher fields (`commission_percent`, `payout_details`, `contact_phone`), the
> `Owner` / `Manager` / `Staff` gradations in `has_permission`, `add_member` / `remove_member`, and
> the Team and Settings screens.

## In scope

- Module + app configuration (`hooks.py`, `modules.txt`, fixtures).
- `Publisher`, `Publisher Member`, `Activity Type`, `Amenity` doctypes.
- Roles `Apna Slot Customer` / `Apna Slot Publisher`, and the permission hook machinery
  (`permission_query_conditions`, `has_permission`) that every later doctype plugs into.
- Signup / login / logout / session bootstrap APIs.
- The frappe-ui SPA scaffold: build config, router, auth guard, app shell, layout for both areas.

## Out of scope

Venues, resources, pricing, bookings, payments. No customer-facing screens beyond auth.

---

## 1. App configuration

### `apna_slot/hooks.py`

```python
app_name = "apna_slot"
app_title = "Apna Slot"
app_publisher = "Apna Slot"
app_description = "Multi-tenant venue slot booking"
app_email = "support@apnaslot.local"
app_license = "mit"

# --- SPA ---------------------------------------------------------------
website_route_rules = [
    {"from_route": "/apnaslot/<path:app_path>", "to_route": "apnaslot"},
]

# --- Tenant isolation (extended by every later phase) ------------------
permission_query_conditions = {
    "Publisher": "apna_slot.permissions.publisher_query",
}
has_permission = {
    "Publisher": "apna_slot.permissions.publisher_has_permission",
}

# --- Fixtures ----------------------------------------------------------
fixtures = [
    {"dt": "Role", "filters": [["role_name", "in", ["Apna Slot Customer", "Apna Slot Publisher"]]]},
    {"dt": "Activity Type"},
    {"dt": "Amenity"},
]
```

`www/apnaslot.html` is the SPA entry template that includes the built `index.html`.

### Directory layout created in this phase

> **Superseded by [02-conventions.md](./02-conventions.md) §1.** The DocTypes are split across two
> modules — `apna_slot_core/` and `apna_slot_booking/` — to stay inside CLAUDE.md's 15-file folder
> limit. The layout below shows the Phase 0 doctypes in their real home.

```
apna_slot/
├─ apna_slot_core/             # module: Apna Slot Core
│  └─ doctype/
│     ├─ publisher/
│     ├─ publisher_member/
│     ├─ activity_type/
│     └─ amenity/
├─ api/
│  ├─ __init__.py
│  ├─ auth.py
│  └─ publisher.py
├─ permissions.py
├─ utils/
│  ├─ __init__.py
│  └─ timezone.py
├─ www/
│  └─ apnaslot.html
├─ public/frontend/            # vite build output (gitignored)
└─ frontend/                   # vite source
```

> DocType folders are created by `bench --site apnaslot.localhost migrate` after the JSON is
> defined through the Desk UI or committed as JSON. Do not `mkdir` them by hand.

---

## 2. DocTypes

### `Publisher`

Naming `PUB-.#####`. The tenant boundary — everything in the system ultimately hangs off one.

| Fieldname | Fieldtype | Options | Notes |
|---|---|---|---|
| `publisher_name` | Data | | **reqd**, unique |
| `status` | Select | `Active`\|`Suspended` | default `Active` |
| `contact_email` | Data | Email | **reqd** |
| `contact_phone` | Data | Phone | |
| `currency` | Link | Currency | **reqd**, default from System Settings; the default for new venues |
| `timezone` | Data | | **reqd**, IANA id; validated against `zoneinfo.available_timezones()` |
| `commission_percent` | Percent | | default `0`; snapshotted onto bookings (D-23) |
| `payout_details` | Small Text | | informational only; no settlement logic exists |
| `members` | Table | Publisher Member | **reqd**, min 1 row |

**Controller `publisher.py`**

- `validate`: timezone is a valid IANA id; `commission_percent` between 0 and 100; at least one
  member with role `Owner`; no duplicate `user` across member rows.
- `before_insert`: if the creating user is not already in `members`, add them as `Owner`.
- `after_insert`: add the `Apna Slot Publisher` role to every member user missing it.
- `on_update`: when a member row is removed, remove the role from that user **only if** they are
  not a member of any other Publisher.

### `Publisher Member` (child)

| Fieldname | Fieldtype | Options | Notes |
|---|---|---|---|
| `user` | Link | User | **reqd**, `in_list_view` |
| `member_role` | Select | `Owner`\|`Manager`\|`Staff` | default `Staff` |

`Owner` and `Manager` may edit venues, resources and pricing. `Staff` may read venues and manage
bookings only. Enforced in `has_permission`, not in the UI.

### `Activity Type`

Naming `field:activity_name`. Seeded fixture, `System Manager`-only write.

| Fieldname | Fieldtype | Notes |
|---|---|---|
| `activity_name` | Data | **reqd**, unique |
| `icon` | Data | lucide icon name, e.g. `lucide-goal` |
| `is_active` | Check | default `1` |

Seeded rows: Football Turf, Cricket Net, Badminton Court, Tennis Court, Basketball Court,
Banquet Hall, Studio, Coworking Desk, Swimming Pool, Table Tennis.

### `Amenity`

Naming `field:amenity_name`. Same shape and permissions as Activity Type.

Seeded rows: Floodlights, Parking, Changing Room, Washroom, Drinking Water, Seating, Cafeteria,
First Aid, Equipment Rental, Air Conditioning, CCTV, Wi-Fi.

---

## 3. Tenant isolation

`apna_slot/permissions.py` is the single place isolation lives. Every later phase adds two
functions here and two lines to `hooks.py`.

```python
def get_user_publishers(user: str | None = None) -> list[str]:
    """Publisher names the user is a member of. Cached per-request."""
```

- Cached with `frappe.cache().hget("apna_slot_publishers", user)`, invalidated in
  `Publisher.on_update` and `on_trash`.
- Returns `[]` for Guest.

```python
def publisher_query(user):        # -> SQL condition string, or ""
def publisher_has_permission(doc, user, permission_type=None):  # -> bool
```

- `System Manager` bypasses both (return `""` / `True`).
- Otherwise: `` `tabPublisher`.name in ('PUB-00001', …) ``, and an empty membership list must
  produce a condition that matches **nothing** (`1=0`), never an empty string. This is the classic
  fail-open bug — it has its own test.

**DocType permission rows** (in the JSON, not runtime): `Apna Slot Publisher` gets
read/write/create on `Publisher`; `Apna Slot Customer` gets nothing. Row-level narrowing is the
hooks' job; the DocType permissions only decide *whether the role may touch the doctype at all*.

---

## 4. APIs

### `apna_slot.api.auth`

| Method | Guest? | Params | Returns |
|---|---|---|---|
| `sign_up` | yes | `email`, `full_name`, `password`, `phone?` | `{"user": "a@b.com"}` |
| `get_session_user` | yes | — | see below |

`sign_up`:
- Rate-limited: `@frappe.rate_limiter(limit=5, seconds=3600)` keyed on IP.
- Rejects an existing enabled user with a generic "could not create account" — never confirm
  whether an address is registered.
- Creates `User` with `user_type = "Website User"`, `send_welcome_email = 0`, then adds the
  `Apna Slot Customer` role, then logs the user in via `frappe.local.login_manager.login_as`.
- Runs `ignore_permissions=True` inside an explicit function, never with a blanket flag.

`get_session_user` returns the SPA's bootstrap payload:

```json
{
  "user": "a@b.com",
  "full_name": "Asha B",
  "is_guest": false,
  "roles": ["Apna Slot Customer", "Apna Slot Publisher"],
  "publishers": [{"name": "PUB-00001", "publisher_name": "Green Field Sports", "member_role": "Owner"}]
}
```

Login and logout use Frappe's built-in `/api/method/login` and `/api/method/logout` (D-27); do not
reimplement them.

### `apna_slot.api.publisher`

| Method | Params | Notes |
|---|---|---|
| `create_publisher` | `publisher_name`, `contact_email`, `contact_phone?`, `currency`, `timezone` | Creates the Publisher with the caller as `Owner`; grants `Apna Slot Publisher`. Refuses if the caller already owns one (Phase 0 limit: one owned Publisher per user). |
| `get_my_publisher` | — | The caller's Publisher with members expanded; `null` if none. |
| `add_member` | `publisher`, `email`, `member_role` | Owner/Manager only. Invites an existing user, or creates a disabled-password Website User and sends a Frappe reset-password link. |
| `remove_member` | `publisher`, `email` | Owner only. Refuses to remove the last `Owner`. |

Venue and resource CRUD in later phases goes through the standard `frappe.client` REST layer via
`useDoc` / `useList` — custom endpoints only where there is non-CRUD logic.

---

## 5. Frontend scaffold

Follow the frappe-ui setup contract exactly: **Vite 5, Tailwind v3**, `exports` subpaths,
`optimizeDeps.exclude: ['frappe-ui']`, `app.use(FrappeUI)`, `vue-router`.

```
frontend/
├─ index.html
├─ vite.config.js          # base: '/assets/apna_slot/frontend/', outDir: '../apna_slot/public/frontend'
├─ tailwind.config.js      # presets: [require('frappe-ui/src/tailwind/preset')]
├─ src/
│  ├─ main.js              # createApp, FrappeUI plugin, router, session bootstrap
│  ├─ router.js
│  ├─ session.js           # useSession(): user, roles, publishers, login/logout/signup
│  ├─ layouts/
│  │  ├─ PublicLayout.vue      # header, footer, no sidebar
│  │  └─ ManageLayout.vue      # DesktopShell + sidebar, MobileShell below md
│  ├─ pages/
│  │  ├─ Login.vue  SignUp.vue
│  │  └─ manage/ Onboarding.vue  Team.vue  Settings.vue
│  └─ components/
```

### Routes introduced in this phase

| Route | Guard | Screen |
|---|---|---|
| `/apnaslot/login` | guest-only | email + password, link to signup |
| `/apnaslot/signup` | guest-only | full name, email, phone, password |
| `/apnaslot/manage` | auth + publisher | dashboard shell (empty in Phase 0) |
| `/apnaslot/manage/onboarding` | auth | create-your-business form; redirect target when a logged-in user has no Publisher |
| `/apnaslot/manage/team` | auth + publisher | member list, add/remove |
| `/apnaslot/manage/settings` | auth + publisher | publisher name, contact, currency, timezone, commission (read-only) |

**Router guards.** `beforeEach` resolves the session once at boot from `get_session_user`.
`meta.requiresAuth` → redirect to `/login?redirect=…`. `meta.requiresPublisher` → redirect to
`/manage/onboarding` when `publishers` is empty.

### frappe-ui usage

- Shell: `DesktopShell` + `MobileShell` in `ManageLayout`; `PublicLayout` is plain.
- Auth forms: `FormControl` with `label` / `description` / `error` / `required` — never
  placeholder-as-label.
- Buttons: `variant="solid" theme="gray"` for primary; never hand-rolled `<button class="bg-…">`.
- Colors: `bg-surface-*`, `text-ink-*`, `border-outline-*` only.
- Team list: `List` / `ListRow` from `frappe-ui/list`. Not `ListView` (legacy).
- Data: `useCall` for the auth/publisher endpoints, `useDoc` for the Publisher settings form with
  `immediate: false` + `submit(params)`.
- Feedback: `toast.success` / `toast.error`; `dialog.confirm` for member removal.
- Icons: `<span class="lucide-users size-4" aria-hidden="true" />`.

---

## 6. Setup commands

```bash
bench --site apnaslot.localhost migrate
bench --site apnaslot.localhost install-app apna_slot   # already installed
cd apps/apna_slot/frontend && yarn install && yarn build
bench --site apnaslot.localhost clear-cache
```

`bench start` runs in the background only, and only if it is not already running.

---

## 7. Acceptance criteria

1. `/apnaslot/signup` creates a Website User with the `Apna Slot Customer` role and an active
   session, and the SPA lands on the customer home.
2. A logged-in customer visiting `/apnaslot/manage` is redirected to `/manage/onboarding`.
3. Completing onboarding creates a `Publisher`, grants `Apna Slot Publisher`, and lands on
   `/manage` without a page reload.
4. Publisher A calling `/api/method/frappe.client.get_list?doctype=Publisher` receives **only**
   their own Publisher. Publisher B's record is absent from the list and returns 403 on direct
   `get`.
5. A user with no Publisher membership gets an empty list, not every Publisher.
6. Adding a member grants that user the publisher role; removing them revokes it unless they
   belong to another Publisher.
7. A Publisher cannot be saved with an invalid timezone string or with zero `Owner` members.
8. The SPA builds and serves at `/apnaslot` with no console errors, in light and dark mode.

## 8. Tests — `apna_slot/tests/test_phase0.py`

| Test | Asserts |
|---|---|
| `test_publisher_creation_grants_role` | role added to owner on insert |
| `test_publisher_requires_valid_timezone` | `ValidationError` on `Mars/Olympus` |
| `test_publisher_requires_owner_member` | `ValidationError` when no `Owner` row |
| `test_query_conditions_scope_to_membership` | user in PUB-A sees only PUB-A |
| `test_query_conditions_fail_closed_for_non_member` | non-member's condition is `1=0`, list is empty |
| `test_system_manager_bypasses_isolation` | admin sees all publishers |
| `test_has_permission_denies_cross_tenant_read` | direct `get_doc` by a non-member raises |
| `test_staff_cannot_write_publisher` | `member_role = Staff` write denied |
| `test_signup_creates_customer_role` | role + `user_type == "Website User"` |
| `test_signup_duplicate_email_is_generic` | error message does not reveal existence |
| `test_remove_last_owner_refused` | `ValidationError` |
| `test_role_revoked_only_when_no_other_membership` | user in two publishers keeps the role |

Run: `bench --site apnaslot.localhost run-tests --app apna_slot --module apna_slot.tests.test_phase0`
