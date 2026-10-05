# QA Review — 8f033c1 `fix(frontend): keep ?redirect across the login and sign-up links`

Reviewed 2026-10-05. Scope: the last commit only — `Login.vue` and `SignUp.vue` (the in-form links
now forward `route.query`), the T-1/T-2/T-3 e2e notes (F-1/F-2 follow-ups), and `scripts/REVIEWS.md`.

## Status: ✅ PASS — one minor finding (F-3), open

## What I verified

| Claim | How | Result |
|---|---|---|
| The built bundle contains the fix | grep `public/frontend/assets/Login-*.js`, `SignUp-*.js` | ✅ `path:"/signup",query:…query`, `path:"/login",query:…query` |
| Guest slot click → login keeps `?redirect` | agent-browser, `:8001`, venue `green-field-sports-arena-2`, 20:00 | ✅ `/login?redirect=/venues/green-field-sports-arena-2` |
| **Create an account** keeps it | clicked the in-form link | ✅ `/signup?redirect=/venues/green-field-sports-arena-2` |
| The reverse link keeps it | `href` of SignUp's **Log in** link | ✅ `/apnaslot/login?redirect=/venues/…` |
| Sign-up lands back on the venue (T-1 step 12) | signed up as `qa-rt-<ts>@example.com` | ✅ lands on `/venues/green-field-sports-arena-2`, signed in, grid shown |
| No open-redirect risk added | `landOn` prefixes `/apnaslot`, so `redirect` stays same-origin | ✅ unchanged behaviour |
| `/login` without a query still links to plain `/signup` | `query: {}` → no query string | ✅ |
| T-2 / T-3 point at the serve note; T-2 step 5 gives the payload | read the diff; the note exists at `t-1-tracer-walk.md:53` | ✅ |

## Findings

### F-3 (minor) — the header **Sign up** / **Log in** buttons still drop `?redirect`

`frontend/src/layouts/PublicLayout.vue:29-30` push a bare `/login` and `/signup`. On
`/login?redirect=/venues/…`, the most visible "Sign up" control is the solid header button, not the
underlined link under the form. Reproduced: open
`/apnaslot/login?redirect=/venues/green-field-sports-arena-2` and click the header **Sign up** →
`/apnaslot/signup` with no query. The new customer then lands on `/` after signing up, which is the
bug this commit set out to fix.

**Fix:** have the header buttons forward `route.query` when the current route is Login or SignUp,
e.g. `router.push({ path: '/signup', query: route.query })`. Add that click to T-1 step 12, or as a
note on it.

### Observations (no action needed)

- Formatting nit: `Login.vue` puts the `>` of the new `<router-link>` on the `class` line, but
  `SignUp.vue` puts it on its own line. Same change in both files, two styles. There is no Prettier
  config to settle it.
- The unit suite isn't affected: this commit changes only frontend and docs files, so I didn't rerun it.
- Test data left behind: user `qa-rt-<ts>@example.com` (no booking made).
