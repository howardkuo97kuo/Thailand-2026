# 清邁員旅地點庫 — project notes for Claude

A planning and in-trip site for a Chiang Mai company trip, **10/15–10/20 2026**, used by three people:
**Charlie, Howard (owner), Lindsay**. Live at https://howardkuo97kuo.github.io/Thailand-2026/
(GitHub Pages, repo `howardkuo97kuo/Thailand-2026`, branch `main` — pushing to main deploys in about a minute).

## Working with Howard
- Reply in **Traditional Chinese**. Keep summaries plain and short; put detail in tables.
- **Suggest first, execute only after he agrees**, unless he says to just do it ("執行", "全部都做", "commit and publish").
- Commit and push only when asked. When asked to publish: push, wait until the live site serves the new
  code, then check the live site and report bugs or "沒有發現 bug".
- He edits the itinerary himself on the site. **Never overwrite live itinerary data without first backing it up
  and re-reading it right before writing**; if it changed meanwhile, stop and merge his edit instead.
- Anything booked (hotels, restaurants, classes, flights) is fixed: shown on 已訂 and locked in 行程.

## Files
- `index.html` — the whole app: HTML, CSS and JS inline, plus the place data. No build step.
- `sw.js` — service worker: offline copy of page, libraries, data, photos, map tiles; network-first for data.
- `manifest.webmanifest`, `icon-*.png`, `og.png` — PWA and share assets.
- `tools/inbox_agent.py` — helper for the 新地點推薦 inbox (Google Places lookup, writes /places).
- `tools/feedback_agent.py` — helper for the 意見 tab (`list`, `propose`, `done`, `fail`).
- `.claude/launch.json` — preview server "site" (python http.server on 127.0.0.1:8765).
- `Thailand-2026/` (nested) — stale local copy, ignored via .git/info/exclude; not part of the site.

## Tabs (order matters to Howard)
挑地點 · 已訂 · 地圖 · 按摩 · 行程 · 新地點推薦 · 意見 — `TABS` in index.html and the tab buttons must match.
During the trip (10/15–10/20, Asia/Bangkok time) the site opens on 行程 at today.

## Data in index.html
- `P` — places: `id, n, c (category), sub, r (region), a, h (hours text), rt, rv, note (我們的備註), m, src
  ("清單" team / "建議" AI), pid (Google place id), tip (小提醒), ll, cd (closed weekdays, 0=Sun), oh (weekly
  minute ranges, Sunday 0:00 based, or "24h"), loc`. Category 其他 is split into `UTIL` (shown on 已訂).
- `CATS`, `REGIONS`, `CAT_COLOR`. `NO_HEART` = 按摩, 課程體驗: shown, mapped, but never hearted.
- `LODGING` (Jhaban Home 10/15–18, THEE Vijit Lanna 10/18–20), `BOOKINGS` (THE HOUSE 10/15 18:30;
  Asia Scenic cooking class 10/16 09:00–14:00), `FLIGHTS` (arrive 10/15 10:25; depart 10/20 17:20 → at the
  airport 14:30).
- `PLAN` — the *default* itinerary per day (titles live here). The real itinerary is in Firebase `/plan`.
- `DAY_TIPS` — hand-written per-day tips; booking to-dos are generated from each day's stops
  (`needsBooking`: notes mentioning 預約/訂位).
- `SPA_RANK` — 按摩 tab tiers/order. Massage shop `note`s hold the recommendation text.

## Firebase Realtime Database
`https://thailand-2026-7304d-default-rtdb.asia-southeast1.firebasedatabase.app`
- `/must` (Charlie's hearts), `/hearts/{howard|lindsay}` — booleans per place id; streamed (EventSource).
- `/plan/{YYYY-MM-DD}` = `{stops:[{t,d,id|hotel|at:"airport",opt?}], by, ts}` — streamed; cached in
  localStorage `cnxPlan`.
- `/inbox`, `/places`, `/removed` — new-place inbox and AI-added places (polled).
- `/feedback/{id}` = `{text, who, ts, status: new→proposed→approved|rejected→done|failed, proposal, result}`.
- Admin secret: `C:\Users\user\.cnx\firebase_secret.txt` — **never print, commit or paste it**; the tools read it.
- Rules are pasted by Howard in the Firebase console. When a change needs a new rule, give him the **complete**
  rules JSON (read the current rules with the secret via `/.settings/rules.json`), not a fragment.
- Keep live streams few: browsers allow ~6 connections per host (hearts ×3 + plan stream; the rest poll).

## Other services
- Google Places API (New): key `GMAPS_KEY` in index.html, restricted to the github.io site and
  localhost:8765 referers, Places API only. Photos load lazily, 5 per place; 429s fall back gracefully.
- Maps: Leaflet 1.9.4 + OpenStreetMap from cdnjs (Maps JavaScript API is not enabled). Drag-sort in 行程
  editing uses SortableJS 1.15.2 from cdnjs, loaded on first edit.

## Scheduled tasks (Claude desktop app, run only while the app is open)
- `cnx-place-inbox` — every 30 min: turns 新地點推薦 submissions into places via `tools/inbox_agent.py`.
- `cnx-feedback-nightly` — 23:00 daily: writes proposals for new 意見, carries out approved ones; skips
  silently when there is nothing.

## 行程 rules the code enforces (keep them when editing)
- Times are on the half hour; consecutive stops at least 30 minutes apart; after a move/add the moved stop
  is retimed from the stop before it (a booking counts from its end, the arrival from `ready`).
- Bookings and flights can't be moved, removed or retimed and are restored if an edit drops them.
- 彈性 (`opt`) stops show as **O**, aren't on the main route line; massage pins/numbers are purple, classes blue;
  route pins carry a ♥n badge; list rows show ♥ marks.
- Each stop warns when the place is closed that weekday or not open at that time (`hoursWarn`).

## How to change things safely
- Edit index.html with small Python patch scripts (in the session scratchpad) that replace exact strings and
  assert each match count, then syntax-check the app script:
  extract the last `<script>…</script>` to a temp `.mjs` and run `node --check`.
- When removing code, list every identifier it defined and grep that none is still used elsewhere
  (deleting `ago()` with the comments feature once broke all itinerary saves).
- Preview with the "site" server; test itinerary edits with `window.fetch` stubbed for `/plan/` writes so the
  real data isn't touched. Leaflet: set the map view before adding circle markers. Off-screen cards use
  `content-visibility`, so read their text with `textContent`, not `innerText`.
- `?now=2026-10-16T13:50` previews a trip moment (next-stop card, today's day) on any device.
- Commit messages end with a `Co-Authored-By:` line for Claude.

## Still open (as of 10/13)
- Firebase rule for `/feedback` has to be published before the 意見 tab can save.
- Bookings to make: Ziri (10/17 17:00), CHUM (10/17), Ekachan (10/18), Makkha (10/20 11:00, KKday/Klook),
  Kiew Kai Ka (10/16), confirm the cooking-class pickup; optional massages/pilates if wanted.
- Lindsay has no hearts yet.
