# 清邁員旅地點庫 — notes for Claude

Planning and in-trip site for a Chiang Mai company trip, **10/15–10/20 2026**, used by **Charlie, Howard
(owner), Lindsay**. Live at https://howardkuo97kuo.github.io/Thailand-2026/ — GitHub Pages from `main` of
`howardkuo97kuo/Thailand-2026`; a push is live in about a minute.

**Read `README.md` first** for the files, `places.json` fields, Firebase paths, the 問 AI chat (Cloudflare
Worker `worker/index.js`, Gemini models and limits), the scheduled tools, local preview and the `sw.js` rules.
This file adds how to work with Howard and what has gone wrong before.

## Working with Howard
- Reply in **Traditional Chinese**; keep summaries plain and short, detail in tables.
- **Suggest first, execute after he agrees**, unless he says to just do it ("執行", "全部都做", "commit and publish").
- Commit and push only when asked. "Publish" means: push, wait until the live site serves the new code, check
  the live site, then report bugs or "沒有發現 bug" and say when it's live.
- Other sessions also push to `main` — `git pull --rebase` before pushing.
- He edits the itinerary on the site himself. **Before writing `/plan`, back it up and re-read it right before
  the write; if it changed, stop and merge his edit** instead of overwriting.
- Anything booked (hotels, restaurants, classes, flights) is fixed: listed on 已訂 and locked in 行程.

## Where things live (beyond README)
- Tab order he chose: 挑地點 · 已訂 · 地圖 · 按摩 · 行程 · 新地點推薦 · 意見 (`TABS` and the tab buttons in
  `index.html` must match). During the trip (Asia/Bangkok dates) the site opens on 行程 at today.
- `index.html` constants: `LODGING`, `BOOKINGS` (THE HOUSE 10/15 18:30; Asia Scenic cooking class 10/16
  09:00–14:00), `FLIGHTS` (arrive 10/15 10:25, ready 11:00; depart 10/20 17:20 → at the airport 14:30),
  `PLAN` (default itinerary; **day titles live here**), `DAY_TIPS` (hand-written tips per day), `SPA_RANK`
  (按摩 tab tiers/order), `NO_HEART` (按摩, 課程體驗: never hearted).
- The real itinerary is Firebase `/plan/{YYYY-MM-DD}` = `{stops:[{t,d,id|hotel|at:"airport",opt?}],by,ts}`,
  streamed live and cached in localStorage `cnxPlan`. Booking to-dos under each day are generated from its stops
  (`needsBooking`: notes that mention 預約/訂位).
- Massage shops' `note` in `places.json` carries our recommendation text (tier, booking advice, which day).
- Firebase rules are pasted by Howard in the console. When a change needs a rule, give him the **complete** rules
  JSON (read the current ones with the secret via `/.settings/rules.json`), never a fragment.
- Keep live streams few: browsers allow ~6 connections per host (3 heart streams + the plan stream; the rest poll).

## 行程 behaviour to preserve
- Half-hour times; consecutive stops ≥ 30 minutes apart; a moved or added stop is retimed from the stop before
  it (a booking counts from its end, the arrival from `ready`); later stops are pushed only when too close.
  Changing a stop's time by hand (`pushLater`) does the same for the stops after it, with an undo toast.
- Bookings and flights can't be moved, removed or retimed, and are put back if an edit drops them.
- 彈性 (`opt`) stops show as **O** and stay off the route line; massage numbers/pins purple, classes blue;
  route pins carry a ♥n badge, list rows ♥ marks; day-map candidate dots are plain (no heart ring).
- Stops warn when the place is closed that weekday or not open at that time (`hoursWarn`).
- `travelWarn` flags a stop whose gap after the previous one is shorter than the estimated trip (walk <0.8 km, else Grab 8 min + 3 min/km; lodging stays 0, out-of-town stops skipped); `sleepWarn` flags back after 22:30 and out before 06:00 the next day.
- Reading/writing live data from this cloud env goes through GitHub Actions: `read-firebase.yml` (`path=all` → `snapshot` branch) and `write-plan.yml` (needs repo secret `FIREBASE_SECRET`; checks `expect_ts`, backs up to `snapshot/backup/`, reads back). Dispatch with `gh api -X POST …/dispatches` (GraphQL/`gh run` are blocked).
- Days before today (Asia/Bangkok) show 已結束 and start folded (header only, no map); 展開/收合 is per visit (`pastOpen`).
- 完成這天 / 取消完成 sets `done:true` on `/plan/{date}` (shared, undoable); a done day folds like a past day with 已完成, and `saveDay` keeps the flag.
- `SUGGEST` (by date) shows a 建議調整 box with 套用 (writes via `saveDay`, undoable) and 不用了 (localStorage `cnxSugOff`);
  each rule works on the live day and returns null once applied. Used when this cloud env can't reach Firebase.

## Changing things safely
- Edit with small patch scripts that replace exact strings and assert each match count; then extract the last
  `<script>` block of `index.html` to a temp `.mjs` and run `node --check` on it.
- When deleting code, list every identifier it defines and grep that none is still used (removing comments once
  deleted `ago()`, which broke every itinerary save).
- Test itinerary edits with `window.fetch` stubbed for `/plan/` writes so real data isn't touched.
- Leaflet: set the map view before adding circle markers. Off-screen cards use `content-visibility`, so read
  their text with `textContent`. `?now=2026-10-16T13:50` previews a trip moment (下一站, today).
- Commit messages end with a `Co-Authored-By:` line for Claude.

## Open items (as of 10/13 night)
- 意見 box is live: `/feedback` rule published 10/14 and tested end to end (submit, proposal, reject, blocked edits).
- Booked: THE HOUSE (10/15 18:30, 3), Baan Landai Old Town (10/15 12:00, 2, under Charlie), cooking class (10/16), Ekachan (10/18 13:00, 3, upstairs; reservation ID kept off the public site),
  Reliever massage (10/15 14:00, 2, Howard, no deposit), CHUM (10/17 12:00, 3, indoor 1F, Howard via Messenger; phone kept off the site),
  ABBY yoga (10/17 09:30, end assumed 10:30), rain tree + sticky waterfall half-day tour (`raintree`, 10/19 05:30 pickup at THEE, back 12:30–13:30, 3).
- Still to book: Kiew Kai Ka (10/16 18:30), Ziri (10/17 16:00),
  Muse Forestias (10/19; 1% Pilates dropped for the tour), Makkha (10/20 11:00, KKday/Klook);
  confirm the cooking-class pickup. Each day's 這天提醒 lists these automatically.
- Flights: Howard and Charlie EVA BR257 (10/15 10:25), Lindsay STARLUX JX751 (10/15 16:05); all three fly
  back together 10/20 17:20 (flight number not given yet).
