# Journey T-1 — the tracer walk

The acceptance walk from [phase-t-tracer.md](../../../specs/phase-t-tracer.md) §2, driven with
agent-browser per [03-testing.md](../../../specs/03-testing.md) §4. Steps 1–9 land in **T-c**;
10 onwards land with the steps that build them and are listed here so the journey is one file.

```bash
export AGENT_BROWSER_SESSION="$(agent-browser session id --scope worktree --prefix apnaslot)"
```

## Publisher — Asha lists a venue

| # | Step | Assertion | Step |
|---|---|---|---|
| 1 | Open `/apnaslot/signup`, sign up as `asha@example.com` | lands on `/apnaslot/` authenticated; header shows the full name | T-b |
| 2 | Click **List your venue** | `/apnaslot/manage/onboarding` | T-b |
| 3 | Create *Green Field Sports*, AED, `Asia/Dubai` | header shows the business name and links to `/manage/venues` | T-b |
| 4 | Open **Venues** | empty state: "No venues yet." | T-c |
| 5 | **New venue** → *Green Field Sports Arena*, Dubai, United Arab Emirates; resource *Turf A*, 60 min, AED 250, 18:00–22:00 | returns to the list; the venue reads **Draft** | T-c |
| 6 | Set the resource to close at 22:30 and submit | error names the row: "Row 1: Monday is open for 270 minutes, which is 30 short of a whole 60-minute slot"; **no second venue is created** on the retry | T-c |
| 7 | **Publish** a venue that has no resource | "Add a bookable resource before publishing *Corner Courts*" — the create form always adds a resource, so the walk cannot reach this; `test_publish_refuses_a_venue_with_no_resource` owns it until Phase 1's wizard can | T-c |
| 8 | **Publish** *Green Field Sports Arena* | the row updates in place to **Published** | T-c |
| 9 | Log out, open `/apnaslot/` | the published venue is listed with "from AED 250 per slot · 1 resource"; the draft venue is not | T-c |

## Customer — Raj books a slot

| # | Step | Assertion | Step |
|---|---|---|---|
| 10 | As a guest, open the venue from the home list | the day grid shows exactly 4 slots for tomorrow, each at AED 250 | T-d |
| 11 | Click a slot while signed out | redirected to `/login?redirect=/venues/...` | T-d |
| 12 | Sign up as `raj@example.com`, navigate back to the venue, pick 19:00 — the login → signup link drops `?redirect`; the round trip is journey 5-2 | checkout shows one line, AED 250, and a countdown starting at 10:00 | T-d |
| 13 | In a second browser, open the same venue | 19:00 reads **Booked** and is disabled — a hold is never revealed as a hold | T-d |
| 14 | In that second browser, POST `booking.create` for 19:00 | HTTP **409**, message "19:00 on 8 Sep is no longer available. Pick another slot." | T-d |
| 15 | **Pay AED 250** | leaves the SPA for `/apnaslot/pay/:token` — a plain card reading "Mock Payment Gateway — no real money moves", the amount, "1 session · Turf A · from 8 Sep", and a countdown; checkout and My Bookings write dates the same way | T-e |
| 16 | Mock pay → **Succeed** | back on checkout: heading reads *Your booking*, badge `Confirmed`, no pay button; the grid shows the slot **Booked** on reload | T-e |
| 17 | Book another slot, pay → **Fail** | badge `Payment Failed`; the slot reads available again on the **next grid read**, not the next sweep | T-e |
| 18 | Book a third slot, pay → **Abandon** | lands back on `/apnaslot/`; the booking stays `Pending Payment` with its ledger row, and only the timer may take it | T-e |
| 19 | Reopen a settled `/pay/:token` | "This payment is already abandoned." — no buttons | T-e |
| 20 | Account menu → **My bookings** | `/apnaslot/bookings` lists the confirmed booking: venue · resource, date and time, AED 250, badge `Confirmed`; a customer with none sees "You have no bookings yet." and **Find a venue** | T-f |
| 21 | Wait one sweep after step 18's hold lapses | that booking reads `Expired` in My Bookings and its slot is available on the grid | T-f |

## Driving notes

- **Salt every email and the business name per run** (`asha.<HHMM>@example.com`,
  *Green Field Sports <HHMM>*) — onboarding refuses a taken business name by name. The site keeps
  earlier walks, so a second
  *Green Field Sports Arena* takes the slug `green-field-sports-arena-2` — read it from
  `search_venues` rather than assuming it.
- **Native time inputs ignore `fill`.** Set them through the value setter so Vue sees the change:
  `agent-browser eval "(()=>{const i=document.querySelectorAll('input[type=time]')[1];Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(i,'22:30');i.dispatchEvent(new Event('input',{bubbles:true}))})()"`
- **Two buttons read "Sign up"** on the signup page — the header's and the form's. Click the form's
  ref, or the header one navigates to the same page and the submit never happens.
- **`bench serve` pins itself to `default_site`** when `common_site_config.json` has one, and then
  ignores the `Host` header — every route 404s with another site's language. Serve this site
  explicitly: `bench --site apnaslot.localhost serve --port 8001`.

## Every run also checks

- **Guest reads nothing but the discovery API** (D-34):
  `GET /api/v2/document/Venue` → 403; `GET /api/v2/method/apna_slot.api.discovery.search_venues`
  → published venues only.
- **Dark mode.** `agent-browser eval "document.documentElement.setAttribute('data-theme','dark')"`,
  then **wait for the transition to settle** before the screenshot — the theme change is animated
  and an immediate shot catches unreadable mid-transition colours.
- **375px.** `agent-browser set viewport 375 800`; `scrollWidth === clientWidth` on every screen.
- **Console.** `agent-browser console` shows no errors. frappe-ui logs
  `Error parsing error response` when vueuse aborts a superseded request; check
  `agent-browser network requests` before chasing it — every request returning 200 means the log is
  the library's abort handler, not a failure.
