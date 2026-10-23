# 清邁員旅地點庫：給 Claude 的工作說明

清邁員旅的規劃與旅途中使用的網站，旅程 **2026/10/15–10/20**，使用者是 **Charlie、Howard（擁有者）、Lindsay**。
網站：https://howardkuo97kuo.github.io/Thailand-2026/ ，GitHub Pages 直接發佈 `howardkuo97kuo/Thailand-2026` 的 `main`，推上去約一分鐘後上線。

**先讀 `README.md`**（檔案、`places.json` 欄位、Firebase 路徑、問 AI 的 Cloudflare Worker、排程工具、本機預覽、`sw.js` 規則），
再讀 **`ARCHITECTURE.md`**（程式怎麼分層、資料怎麼流動、已知限制）。本檔補充怎麼跟 Howard 合作，以及踩過的坑。

## 跟 Howard 合作
- 用**繁體中文**回覆，結論先行，摘要簡短，細節放表格。
- 凡是要他選的，一律用**可點選的選擇題卡片**並標示推薦，不要用文字編號題。
- **先建議，他同意後再執行**；他說「執行」、「全部都做」、「直接部署」才直接做。
- 只在被要求時 commit 與 push。「發佈」的意思是：推上 `main`，等線上網站換成新程式，打開線上網站檢查，回報問題或「沒有發現 bug」，並說明何時上線。
- 其他討論串也會推 `main`，推送前先 `git pull --rebase`。
- 他會自己在網站上改行程。**寫入 `/plan` 之前先備份，寫入前再重讀一次；若有變動就停下來合併他的修改**，不要覆蓋。
- 同一天的多個修改先合併成一次寫入，避免反覆測試與部署。
- 回報「誰按了愛心」之前，先重新讀取最新資料（曾誤說火鍋三人都按愛心，其實 Charlie 沒有）。
- 已訂的項目（住宿、餐廳、課程、機票）視為固定：列在「已訂」，並在「行程」鎖定。
- 電話號碼與訂位代號不放上公開網站。Firebase 密鑰不要請他貼在聊天，由他自己放進 GitHub Secrets。
- 網站相關需求都集中在「清邁行程網站維護」這個討論串處理，不另開新串。

## 程式裡的重要位置（補充 README）
- 分頁順序是他選的：挑地點 · 已訂 · 地圖 · 按摩 · 行程 · 新地點推薦 · 意見。`index.html` 的 `TABS` 與分頁按鈕必須一致。
  旅途中（以 Asia/Bangkok 日期判斷）網站會直接開在「行程」的今天。
- `index.html` 內的常數：`LODGING`、`BOOKINGS`（THE HOUSE 10/15 18:30；Asia Scenic 廚藝課 10/16 09:00–14:00 等）、
  `FLIGHTS`（10/15 10:25 抵達、11:00 可出發；10/20 17:20 起飛，要 14:30 到機場）、
  `PLAN`（預設行程，**每天的標題在這裡**）、`DAY_TIPS`（每天手寫的提醒）、`SPA_RANK`（按摩分頁的分級與順序）、
  `NO_HEART`（按摩、課程體驗不能按愛心）。
- 真正的行程在 Firebase `/plan/{YYYY-MM-DD}` = `{stops:[{t,d,id|hotel|at:"airport",opt?}],by,ts,done?}`，
  即時推送，並快取在 localStorage `cnxPlan`。每天底下的待訂提醒由該天的行程自動產生（`needsBooking`：備註含「預約」或「訂位」）。
- 按摩店的 `note`（在 `places.json`）寫著我們的推薦：分級、預約建議、建議哪一天。
- Firebase 規則由 Howard 在主控台貼上，規則**不在 repo**。需要改規則時，給他**完整**的規則 JSON
  （用密鑰讀 `/.settings/rules.json` 取得目前版本），不要給片段。
- 即時連線要少：瀏覽器對每個主機約允許 6 條連線（3 條愛心串流加 1 條行程串流，其餘用輪詢）。

## 行程分頁要保留的行為
- 時間以半小時為單位；相鄰兩站至少相隔 30 分鐘。移動或新增的站從前一站重新排時間（預約從結束時間算，抵達從 `ready` 算），後面的站只有太近才往後推。
  手動改某站時間（`pushLater`）也會對後面的站做同樣處理，並跳出可復原的提示。
- 預約與航班不能移動、刪除或改時間，被編輯弄掉時會自動放回。
- 彈性站（`opt`）顯示為 **O**，不連到路線上；按摩的編號與標記是紫色，課程是藍色；
  路線上的標記帶 ♥n 徽章，清單列有 ♥；當天地圖上的候選點是素色（沒有愛心外圈）。
- 當天公休或不在營業時間時，該站顯示警告（`hoursWarn`）。
- `travelWarn`：與前一站的間隔短於估計車程就警告（步行小於 0.8 km；否則 Grab 8 分鐘加每公里 3 分鐘；住宿算 0；郊區景點與小於 6 分鐘的不警告）。
  `sleepWarn`：晚上 22:30 後才回、隔天 06:00 前就出發時警告。
- 今天以前的日子顯示「已結束」並預設收合（只有標題，沒有地圖），「展開／收合」只在這次瀏覽有效（`pastOpen`）。
- 「完成這天」／「取消完成」會在 `/plan/{date}` 設 `done:true`（共用、可復原）；完成的天和過去的天一樣收合並顯示「已完成」，`saveDay` 會保留這個旗標。
- `SUGGEST`（依日期）會顯示「建議調整」方塊，有「套用」（用 `saveDay` 寫入，可復原）和「不用了」（存 localStorage `cnxSugOff`）。
  每條規則都針對當下的行程，套用後必須回傳 null。這是雲端環境連不到 Firebase 時的替代做法，現在已可直接寫入，新增規則前先想想是否需要。

## 從雲端環境讀寫即時資料
雲端環境連不到 Firebase、github.io 與 Cloudflare Worker，所以透過 GitHub Actions：
- 讀：`.github/workflows/read-firebase.yml`（`path=plan` 或 `all`），結果放在 `snapshot` 分支的 `snapshot/<path>.json`。
- 寫：`.github/workflows/write-plan.yml`，輸入 `date`（限 `2026-10-15` 到 `2026-10-20`）、`expect_ts`、`payload`。需要 repo secret `FIREBASE_SECRET`。
  它會比對 `expect_ts`、先備份到 `snapshot/backup/`、寫入後讀回比對。
- 用 `gh api -X POST repos/howardkuo97kuo/Thailand-2026/actions/workflows/<檔名>/dispatches -f ref=main -f 'inputs[...]=...'` 觸發。
  GraphQL 與 `gh run` 會被擋，用 REST；工作紀錄在被擋的主機上，失敗原因看 check-run 的 annotation。
- 做法：重讀當天 → 組新內容（`ts` 用現在毫秒，保留 `done`）→ 觸發 → 輪詢 `workflows/write-plan.yml/runs?per_page=1` 直到完成 → 讀結果。
- 若失去 repo 的 GitHub 權限，用 `add_repo`（owner `howardkuo97kuo`、repo `Thailand-2026`、`access:"push"`）重新加入。

## 安全地修改
- 用小的修補腳本替換精確字串，並斷言每一處的命中次數；然後把 `index.html` 最後一個 `<script>` 區塊取出存成暫存 `.mjs`，用 `node --check` 檢查。
- 刪程式碼前，列出它定義的所有識別字，並 grep 確認沒有其他地方還在用（刪掉註解時曾連帶刪掉 `ago()`，讓所有行程存檔壞掉）。
- 測試行程修改時，把 `window.fetch` 對 `/plan/` 的寫入換成假的，避免動到真資料。
- Leaflet：先設定地圖視角，再加圓形標記。畫面外的卡片用了 `content-visibility`，要讀文字請用 `textContent`。
  `?now=2026-10-16T13:50` 可預覽旅程中的某個時刻（「下一站」、今天）。
- 避免用會比對到自己指令列的 `pkill -f`。
- commit 訊息依環境指示結尾加上 Claude 的 `Co-Authored-By:` 行。

## 已知限制（如實記錄）
- 清邁專屬值寫死在程式裡：日期、`Asia/Bangkok`、Firebase 網址、Worker 網址、`cnx` 開頭的 localStorage 鍵與 `cnx-v3` 快取名、`write-plan.yml` 的日期範圍。
- 預設行程、住宿、訂位、航班等資料與程式一起放在 `index.html`（約 2,450 行），不在 JSON。
- Firebase 規則只存在主控台，沒有存檔。「只有 Howard 能同意執行」目前只是前端檢查。
- 問 AI 的限流在 Worker 實例各算各的，不可靠；細節見 README。
- `GMAPS_KEY` 寫在 `index.html`（公開，靠 Google Cloud 的 API 與來源網址限制保護）。

## 開放項目（旅程已於 10/20 結束，以下為 10/19 夜的最後狀態）
- 已訂：THE HOUSE（10/15 18:30，3 人）、Baan Landai Old Town（10/15 12:00，2 人，Charlie 名下）、廚藝課（10/16）、
  Ekachan（10/18 13:00，3 人，樓上；訂位代號不放公開網站）、Reliever 按摩（10/15 14:00，2 人，Howard，免訂金）、
  CHUM（10/17 12:00，3 人，一樓室內，Howard 用 Messenger 訂；電話不放網站）、ABBY 瑜伽（10/17 09:30，結束時間假設 10:30）、
  雨樹加黏黏瀑布半日遊（`raintree`，10/19 05:30 在 THEE 接送，12:30–13:30 回到，3 人）。
- 當時未訂：Kiew Kai Ka（10/16 18:30）、Ziri（10/17 16:00）、Makkha（10/20 11:00，KKday/Klook）；10/18 的 1% Pilates 一直沒鎖成已訂（缺人數與結束時間）。
- 航班：Howard 與 Charlie 搭長榮 BR257（10/15 10:25 抵達），Lindsay 搭星宇 JX751（10/15 16:05）；三人 10/20 17:20 一起回程（航班號碼一直沒有給）。
- 10/19 實際：半日遊後都在飯店（午餐、做蠟燭、泡冰塊澡），16:30 Scoof 下午茶，晚餐 Dash Teak House 18:30，20:30 回 THEE。
- 意見箱已上線：`/feedback` 規則 10/14 發佈，並完整測過（送出、建議、拒絕、被擋的修改）。
