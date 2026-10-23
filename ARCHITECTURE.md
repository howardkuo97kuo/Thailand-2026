# 架構說明

清邁員旅網站的程式怎麼分層、資料怎麼流動、哪些地方有限制。怎麼操作與部署見 `README.md`，怎麼跟 Howard 合作見 `CLAUDE.md`。
行號只是指引，改版後會偏移，請用函式名稱搜尋。

## 一句話

一個沒有建置步驟的靜態網站（GitHub Pages），瀏覽器直接用 REST／SSE 讀寫 Firebase Realtime Database；
離線靠 service worker；問 AI 經由一個 Cloudflare Worker 呼叫 Gemini；Claude 與排程工具則在瀏覽器之外讀寫同一份 Firebase。

```
                       ┌────────────────────── GitHub (main) ──────────────────────┐
   瀏覽器（3 人）       │ index.html  places.json  sw.js  worker/  tools/  workflows │
   index.html + sw.js ◄─┤ GitHub Pages 直接發佈 main                                 │
        │  │  │         └───────────────────────────────────────────────────────────┘
        │  │  └─ POST ─► Cloudflare Worker cnx-chat ──► Gemini（免費層，逐字回傳）
        │  └──── REST + SSE（不登入，權限由規則決定）
        ▼
   Firebase Realtime DB  ◄── tools/*.py（排程 Claude 任務，用密鑰讀寫）
        ▲
        └── GitHub Actions read-firebase / write-plan（用 FIREBASE_SECRET）◄── 雲端的 Claude（gh api）
```

## 檔案與責任

| 檔案 | 責任 |
| --- | --- |
| `index.html` | 樣式（約 700 行）、版面、全部邏輯（最後一個 `<script>`，約 1,600 行，包在一個 IIFE 裡），以及行程資料常數 |
| `places.json` | `cats`、`regions`、`places`；網頁與 `tools/` 讀同一份。內建地點的唯一來源 |
| `sw.js` | 離線快取，見下文「離線」 |
| `worker/index.js` | 問 AI 的後端，只做轉送、規則、模型輪替 |
| `tools/cnx_common.py` | 排程工具共用：Firebase REST（帶密鑰）、讀 `places.json` |
| `tools/inbox_agent.py` | 把 `/inbox` 的推薦地點用 Google Places 查好，寫進 `/places` |
| `tools/feedback_agent.py` | 把 `/feedback` 的意見整理成建議；Howard 同意後才真的修改 |
| `.github/workflows/read-firebase.yml`、`write-plan.yml` | 讓雲端的 Claude 讀寫 Firebase（見「Claude 的讀寫橋接」） |
| `docs/superpowers/` | 問 AI 當初的設計與計畫文件，只供參考 |

## 前端分層（`index.html` 的 script）

沒有框架，狀態放在模組內的變數，畫面用字串模板重畫。由上到下大致是：

1. **資料常數**：`CATS`/`REGIONS`/`P`（來自 `places.json`）、`PLAN`（預設行程）、`BOOKINGS`、`FLIGHTS`、`LODGING`、`PEOPLE`、`NO_HEART`、`SPA_RANK`、`DAY_TIPS`、`TRIP_DAYS`。
   這些是「清邁專屬」的部分，也是最難複製到別的旅程的部分。
2. **地點與照片**：`placeById`、`loadLive`（Google Places API (New) 取營業時間與照片，每個地點最多 `MAX_PHOTOS` 張）、燈箱、地點彈窗。
3. **挑地點**：`filtered`／`sortCmp`／`card`／`table`／`render`，篩選條件同步到網址（`readUrlState`／`writeUrlState`）。
4. **愛心**：三個人各一條路徑（見下表），`remote[who]` 存各人的愛心，`updatePlaces` 只重畫有變的地點。
5. **分頁與地圖**：`TABS`／`setTab`，Leaflet 地圖（`drawMarkers`、`addRoute`、`drawPlanMap`），資料來源是 OpenStreetMap 圖磚。
6. **行程**：`renderPlan`／`daySection`／`renderDay`。每天的內容是「預設 `PLAN`」被 Firebase 的 `/plan/{date}`（`PLAN_LIVE`）蓋過；
   `dayStops` 取當下生效的那份。排序用 Sortable，改動走 `saveDay`，寫入走 `putPlan`。
   檢查與提示：`hoursWarn`、`travelWarn`、`sleepWarn`、`needsBooking`／`dayTodos`、`SUGGEST`。
   時間規則由 `retime`／`pushLater` 實作，預約與航班由 `bookedOn`／`isFixed` 鎖定。
7. **推薦與意見**：`submitInbox`／`renderInbox`、`submitIdea`／`decideIdea`／`renderIdeas`。
8. **問 AI**：`chatContext()` 把網站資料組成不超過 30,000 字的摘要，`chatSend` 送到 Worker 並逐字顯示。
9. **同步**：檔案最後的 `FB`、`pull`／`listen`／`liveJSON`／`startPlanLive`、`setSync`，以及 service worker 註冊。

## 資料流

### 地點
內建地點來自 `places.json`；人們推薦的地點先進 `/inbox`，`inbox_agent.py` 查好 Google 資料後寫進 `/places`，
網頁用 `liveJSON("places")` 收到後由 `mergeAdded` 併進 `P`；被移除的地點記在 `/removed`。

### Firebase 路徑

| 路徑 | 誰寫 | 內容 |
| --- | --- | --- |
| `/must`、`/hearts/howard`、`/hearts/lindsay` | 網頁（按愛心） | `{地點id: true/false}`；Charlie 沿用舊的 `/must` |
| `/plan/{YYYY-MM-DD}` | 網頁、Claude（write-plan） | `{stops:[{t,d,id｜hotel｜at,opt?}],by,ts,done?}`；`ts` 是毫秒時間，用來偵測衝突 |
| `/inbox`、`/places`、`/removed` | 網頁（inbox）、`inbox_agent.py`（places、removed） | 推薦收件匣、agent 加入的地點、被移除的地點 |
| `/feedback` | 網頁、`feedback_agent.py` | 意見、AI 建議、Howard 的決定 |

### 即時更新與連線數
瀏覽器對同一主機約允許 6 條連線，所以只有 3 條愛心串流和 1 條行程串流用 `EventSource`（SSE），
其餘（`/places`、`/removed`、`/inbox`、`/feedback`）用 `liveJSON` 輪詢。串流開不起來時，行程每 8 秒、愛心每 30 秒補抓一次。
`applyPlan` 只重畫有變的那一天，而且不會打斷使用者正在輸入的欄位（等 blur 才重畫）。

### 行程的保護
- 預約與航班（`BOOKINGS`、`FLIGHTS`）鎖定：不能移動、刪除、改時間，編輯弄掉時自動補回。
- 每次改動都先經過 `retime`（半小時為單位、相鄰至少 30 分鐘），再 `saveDay`；多數操作有 5 秒可復原（`UNDO_MS`）。
- 快取在 localStorage `cnxPlan`，離線時顯示上次的行程。

## 離線（`sw.js`）

| 請求 | 策略 |
| --- | --- |
| 同網域頁面（`SHELL`） | 網路優先，但慢網路只等 2.5 秒就先顯示快取，背景繼續更新 |
| Firebase、Places 資料 | 網路優先，離線用上次的資料（`cnx-data`） |
| Places 照片、OSM 圖磚 | 快取優先（`cnx-photos` 400 張、`cnx-tiles` 600 張上限） |
| cdnjs、Google Fonts 等函式庫 | 快取優先（`cnx-lib`） |
| SSE 串流、非 GET | 不處理 |

改了快取規則或 `SHELL` 時，把 `V`（目前 `cnx-v3`）加一號，舊快取才會清掉；新增同網域檔案要加進 `SHELL`。

## 問 AI

網頁送「最多 12 則、每則 500 字的對話」加「網站資料摘要」給 Worker，Worker 加上規則（只答清邁行程）與 `GEMINI_API_KEY`，
依序試 `MODELS`，遇到過載或額度用完就換下一個，再把回答逐字傳回，並在 `X-Model` 標頭標示用了哪個模型。
Worker 的 `SEARCH = false`，所以網站以外的問題只憑模型知識回答。限流與額度的取捨見 README。

## Claude 的讀寫橋接

雲端環境連不到 Firebase，所以 Claude 透過 GitHub Actions：

1. **讀**：觸發 `read-firebase.yml`（`path=plan｜all｜某路徑`）→ 把資料存到 `snapshot` 分支的 `snapshot/<path>.json`（沿用該分支原有檔案）→ 用 `gh api` 取回。
2. **寫**：觸發 `write-plan.yml`（`date`、`expect_ts`、`payload`）→ 檢查日期在 10/15–10/20 之間 → live 的 `ts` 與 `expect_ts` 不同就拒絕 →
   備份 live 那天到 `snapshot/backup/plan-{date}-{ts}.json` → 用 `FIREBASE_SECRET` 寫入 → 讀回比對。
3. 失敗原因看 check-run 的 annotation（工作紀錄在雲端環境連不到的主機上）。

排程的 `tools/*.py` 則在 Howard 的電腦上，用 `%USERPROFILE%\.cnx\firebase_secret.txt` 直接讀寫。

## 金鑰與服務位置

| 項目 | 放哪裡 | 備註 |
| --- | --- | --- |
| Firebase 資料庫密鑰 | GitHub Secret `FIREBASE_SECRET`；本機工具讀 `~\.cnx\firebase_secret.txt` | 不 commit、不印出、不貼到聊天 |
| Google Places 金鑰 | `index.html` 的 `GMAPS_KEY`（公開） | 靠 Google Cloud 限制 API 與來源網址保護 |
| Gemini 金鑰 | Cloudflare Worker Secret `GEMINI_API_KEY` | 不在 repo |
| Firebase 規則 | 只在 Firebase 主控台 | repo 沒有存檔，要改時給 Howard 完整 JSON |
| Worker | 手動貼到 Cloudflare 主控台部署 | 改了 `worker/index.js` 要重新部署 |

## 已知限制與取捨

- **規則不在 repo**：資料庫不登入，所有權限由主控台的規則決定；「只有 Howard 能同意執行」目前只是前端檢查。
- **清邁專屬值寫死**：日期（`TRIP_DAYS`、`write-plan.yml`）、`Asia/Bangkok`、Firebase 與 Worker 網址、`cnx` 前綴的鍵與快取名。
- **資料混在程式裡**：預設行程、住宿、訂位、航班都在 `index.html`；每天的標題在 `PLAN`。改一天要動約 200 KB 的檔案。
- **Worker 限流不可靠**：計數是每個實例各算各的，偽造來源的人可用光當天的免費額度（拿不到金鑰，也沒有費用）。
- **串流連線數有上限**：新增即時路徑前先算連線數。
- **`SUGGEST` 規則是舊時代的產物**：當時雲端連不到 Firebase，現在可以直接寫入；規則要回傳 null 才會在套用後消失。
