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
| 7 | **Publish** a venue that has no resource | "Add a bookable resource before publishing *Corner Courts*" | T-c |
| 8 | **Publish** *Green Field Sports Arena* | the row updates in place to **Published** | T-c |
| 9 | Log out, open `/apnaslot/` | the published venue is listed with "from AED 250 per slot · 1 resource"; the draft venue is not | T-c |

## Customer — Raj books a slot

| # | Step | Assertion | Step |
|---|---|---|---|
| 10 | Sign up as `raj@example.com`, open the venue page | the day grid shows exactly 4 slots for tomorrow, each at AED 250 | T-d |
| 11 | Pick 19:00 | checkout shows one line, a 10-minute countdown | T-d |
| 12 | Mock pay → **Succeed** | booking is `Confirmed` | T-e |
| 13 | Open **My Bookings** | the booking is listed | T-f |
| 14 | Reload the grid | 19:00 reads **Booked** | T-d |

## Every run also checks

- **Guest reads nothing but the discovery API** (D-34):
  `GET /api/v2/document/Venue` → 403; `GET /api/v2/method/apna_slot.api.discovery.search_venues`
  → published venues only.
- **Dark mode.** `agent-browser eval "document.documentElement.setAttribute('data-theme','dark')"`,
  then **wait for the transition to settle** before the screenshot — the theme change is animated
  and an immediate shot catches unreadable mid-transition colours.
- **375px.** `agent-browser set viewport 375 800`; `scrollWidth === clientWidth` on every screen.
- **Console.** `agent-browser console` is empty.
