# Phase E — Playwright E2E suite and UI Tests CI

**Goal:** the E2E layer in [03-testing.md](./03-testing.md) runs unattended, on every pull request,
the way Hive (`apps/bwh_hive`) runs its own: Playwright specs against a real bench in GitHub
Actions. The agent-browser journeys stay the exploratory layer; the specs are the regression net.

The setup is copied from Hive file for file, renamed for this app. Where Hive's shape does not fit,
the difference is listed in §4 and nowhere else.

---

## 1. What ships

| Hive | Apna Slot | Job |
|---|---|---|
| `.github/workflows/ui-tests.yml` | same | Bench + MariaDB + Redis, `apnaslot.test` in `/etc/hosts`, seed, `bench start`, locator lint, `playwright test`, report artefacts, bench logs on failure |
| `package.json` (root) | same | `@playwright/test`; `test:e2e`, `test:e2e:ui`, `test:e2e:headed`, `test:e2e:debug`, `test:e2e:lint` |
| `playwright.config.ts` | same | `setup` → `chromium` (Administrator) and `customer-setup` → `customer` (Hive: `client-setup` → `client`); one worker, retries in CI, trace on retry |
| `e2e/tsconfig.json` | same | |
| `e2e/no-markup-locators.mjs` | same | Fails a spec that keys off CSS classes, `:has-text()` or tag selectors |
| `e2e/helpers/{auth,frappe,index}.ts` | same | Login; REST helpers over `127.0.0.1` + `Host` |
| `e2e/helpers/{app,ui}.ts` | same, rewritten | The suite's `test` + `GUEST` state; SPA locators and flows (`holdSlot`, `payWith`, `selectOption`) |
| `e2e/helpers/hive.ts` | `e2e/helpers/apna_slot.ts` | Domain helpers: test venue, booking, payment, cleanup |
| `e2e/pages/index.ts` | same | Page objects, added as needed |
| `e2e/tests/auth.setup.ts`, `client-auth.setup.ts` | `auth.setup.ts`, `customer-auth.setup.ts` | Session + CSRF saved to `e2e/.auth/` |
| `bwh_hive/e2e_seed.py` | `apna_slot/e2e_seed.py` | `bench execute apna_slot.e2e_seed.setup_e2e_data` |
| `.gitignore` Playwright block | same | `e2e/.auth/`, `playwright-report/`, `test-results/` |

## 2. Seed data

`setup_e2e_data` is idempotent and builds through the real controllers ([03-testing.md](./03-testing.md)
rule 7):

- **Administrator** owns the publisher *E2E Sports* (AED, `Asia/Dubai`) — the `chromium` project's
  user is a publisher, as Hive's Administrator is a team member.
- *E2E Sports Arena*, published, with *Turf A*: 60 min, AED 250, 18:00–22:00 every day.
- **customer@example.com** / `admin`, an `Apna Slot Customer` with no publisher — the `customer`
  project's user.

Specs that consume slots create their own salted venue through the REST helpers, so a retry or a
rerun on a dev site never finds its slot already taken.

## 3. Specs

Each ports a slice of a T journey. Ids in brackets are the journey steps.

| Spec | Project | Asserts |
|---|---|---|
| `discovery.spec.ts` | guest | Seeded venue listed "from AED 250 per slot · 1 resource" [T-1·9]; 4 slots tomorrow [T-1·10]; slot click redirects to login [T-1·11] |
| `venues.spec.ts` | chromium | New venue form creates a **Draft** [T-1·5]; a short closing time names the row [T-1·6]; **Publish** flips the row in place [T-1·8] |
| `booking.customer.spec.ts` | customer | Hold → checkout → mock **Succeed** → `Confirmed`, grid reads **Booked**, My bookings lists it [T-1·12,15,16,20]; **Fail** frees the slot [T-1·17]; **Abandon** keeps the hold [T-1·18]; a settled link shows no buttons [T-1·19] |
| `race.customer.spec.ts` | customer | A holds 19:00; B (a second browser, as Administrator) sees **Booked** and its `booking.create` gets 409 naming the slot; A has exactly one booking [T-2] |

T-3 (expiry) stays an agent-browser journey: it waits on the scheduler, and the suite never sleeps
(rule 4). The job itself is covered by `test_expiry_job_releases_hold`.

## 4. Where this differs from Hive

- **Local site.** Defaults point at `apnaslot.localhost:8000`. On a bench whose `default_site` is
  another site, export `BASE_URL`, `SITE_HOST` and `API_BASE` for the `--port 8001` server
  ([03-testing.md](./03-testing.md) §3).
- **CSRF.** Hive reads `frappe.csrf_token` from `/app`; a customer is a Website User and has no
  desk, so both setups read the SPA's boot value `window.csrf_token` from `/apnaslot`.
- **Branch.** CI triggers on pushes to `main`, this repo's default branch.
- **Project split.** Hive picks its client spec by name (`/client-experience/`); here any
  `*.customer.spec.ts` runs as the customer, and the `customer` project also depends on `setup`
  because its specs create venues through the Administrator's REST helpers.
- **`app.ts`.** Hive's fixture suppresses an overdue dialog through localStorage. Apna Slot has no
  such overlay, so `test` is the base `test`, kept as the single import point; `GUEST` and
  `tomorrowISO()` live there instead.
- **One `data-testid`.** `venue-row` on the publisher's venue list: a row is a plain `div` with
  no role to filter by.
- **Cleanup unlists rather than deletes.** A test venue's bookings are ledger history; unlisting
  keeps the home page from growing every run.

## 5. Build order

| Step | Deliverable |
|---|---|
| E-a | Root `package.json`, `playwright.config.ts`, `e2e/` skeleton, helpers, auth setups, `.gitignore` |
| E-b | `e2e_seed.py` |
| E-c | The four specs, green locally against `apnaslot.localhost` |
| E-d | `.github/workflows/ui-tests.yml`; docs in README and [03-testing.md](./03-testing.md) |
