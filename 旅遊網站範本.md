# 旅遊行程網站範本（放進新 repo 的 CLAUDE.md）

從清邁員旅網站（howardkuo97kuo/Thailand-2026）整理而來。開新旅程時，把本檔複製成新 repo 的 `CLAUDE.md`，並填完第 1 節的欄位。凡是寫成 `{{欄位}}` 的地方都要換掉。

## 0. 給 Claude 的開場指令
1. 先請使用者填第 1 節；缺的欄位用點選選擇題問，不要猜。
2. 填完後，在新 repo 搜尋 `cnx`、`Thailand`、`Bangkok`、`清邁`、`2026-10`，確認沒有殘留。
3. 做完用 `node --check` 檢查腳本，推上 `main`，等網站上線後打開確認。

## 1. 旅程設定（每次必填）
| 欄位 | 說明 | 清邁站的值（範例） | 台灣站 |
|---|---|---|---|
| `{{TRIP_NAME}}` | 網站名稱 | 清邁員旅地點庫 | |
| `{{REGION}}` | 國家或城市 | 泰國清邁 | 台灣（城市？） |
| `{{START}}` / `{{END}}` | 日期 | 2026-10-15 到 2026-10-20 | |
| `{{TZ}}` | 時區 | Asia/Bangkok | Asia/Taipei |
| `{{TRAVELLERS}}` | 成員與擁有者 | Charlie、Howard（owner）、Lindsay | |
| `{{REPO}}` | GitHub repo | howardkuo97kuo/Thailand-2026 | |
| `{{SITE_URL}}` | Pages 網址 | https://howardkuo97kuo.github.io/Thailand-2026/ | |
| `{{FB_DB}}` | Firebase 資料庫網址 | thailand-2026-7304d-default-rtdb… | 新建一個 |
| `{{WORKER}}` | Cloudflare Worker 名稱與網址 | cnx-chat | |
| `{{PREFIX}}` | 前綴，用於 localStorage 鍵與工具檔名 | cnx | |
| `{{CATS}}` | 地點分類 | 景點、美食、咖啡甜點、按摩、課程體驗、購物市集 | |
| `{{REGIONS}}` | 地區 | 古城、尼曼、北區…… | |
| `{{TRANSPORT}}` | 交通估算 | Grab：8 分鐘＋3 分鐘每公里；步行小於 0.8 公里 | |
| `{{FOOD_AWARD}}` | 美食標章 | 米其林必比登 | |
| `{{CURRENCY}}` | 貨幣 | 銖 | 新台幣 |

## 2. 與使用者合作的規則
- 用**繁體中文**回覆，摘要簡短，細節放表格。
- 凡是要使用者選的，一律用**點選卡片並附推薦**，不要用文字編號題。
- 涉及檔案或多步驟任務，先用選擇題釐清再動手；使用者說「執行」、「全部都做」才直接做。
- 只在被要求時 commit 與 push。「發佈」代表：推上 `main`，等網站上線，打開確認，回報「沒有發現 bug」或列出問題與上線時間。
- 其他討論串也會推 `main`，推送前先 `git pull --rebase`。
- 使用者會自己在網站上改行程。**寫入 `/plan` 前先備份，寫入前再重讀一次；若有變動，停下來合併。**
- 已訂項目（住宿、餐廳、課程、機票）視為固定：列在「已訂」並在行程中鎖定。
- 同一天的多個改動先合併，一次寫入。
- 回報「誰按了愛心」「誰要去」之前，先重新讀取最新資料。

## 3. 檔案結構
| 檔案 | 內容 |
|---|---|
| `index.html` | 網站的版面與邏輯。**建議資料不要寫在這裡** |
| `trip.json`（建議新增） | 日期、成員、住宿 `LODGING`、訂位 `BOOKINGS`、航班或交通 `FLIGHTS`、預設行程 `PLAN`、每日提醒 `DAY_TIPS` |
| `places.json` | `cats`、`regions`、`places`（欄位見下） |
| `sw.js` | 離線快取；改規則時 `V` 加一號，新增同網域檔案要加進 `SHELL` |
| `manifest.webmanifest`、`icon-*.png`、`og.png` | 加到主畫面與分享預覽 |
| `worker/index.js` | 問 AI 的 Cloudflare Worker |
| `tools/` | 推薦地點與意見的排程工具（`inbox_agent.py`、`feedback_agent.py`、`{{PREFIX}}_common.py`） |
| `.github/workflows/read-firebase.yml`、`write-plan.yml` | Claude 讀寫行程的橋接 |
| `firebase-rules.json`（建議新增） | Firebase 規則存檔，需手動貼到主控台，不含密鑰 |

`places.json` 欄位：`id`、`n` 名稱、`loc` 說明、`c` 分類、`sub`、`r` 地區、`a` 地址、`h` 營業時間文字、`cd` 公休星期（0 為週日）、`oh` 每週營業分鐘區間（從週日 00:00 起算）、`rt` 評分、`rv` 評論數、`pid` Google Place ID、`ll` 經緯度、`note` 備註、`tip` 小提醒、`src`、`m` 擁有者預設愛心、`mich` 美食標章（選填）。

## 4. Firebase 資料
| 路徑 | 用途 |
|---|---|
| `/must`、`/hearts/{人}` | 愛心 |
| `/plan/{YYYY-MM-DD}` | 每日行程 `{stops:[{t,d,id|hotel|at,opt?}],by,ts,done?}` |
| `/inbox`、`/places`、`/removed` | 推薦地點收件匣、agent 加入的地點、被移除的地點 |
| `/feedback` | 意見與 AI 建議 |

- 網頁不登入，直接用 REST；權限由規則決定。規則給使用者時要給**完整 JSON**，不要給片段。
- 即時連線要少：每個網域瀏覽器約 6 條，3 條愛心加 1 條行程，其餘用輪詢。

## 5. 行程行為（要保留）
- 時間以半小時為單位；相鄰兩站至少相隔 30 分鐘；移動或新增的站從前一站重新排時間，後面的只有太近才推遲。
- 預訂與交通班次不能移動、刪除或改時間。
- 彈性站（`opt`）顯示為 O，不連上路線。
- `hoursWarn`：當天公休或不在營業時間內時警告。
- `travelWarn`：與前一站的間隔短於估計交通時間就警告（用 `{{TRANSPORT}}` 的公式）。
- `sleepWarn`：晚上 22:30 後才回、隔天 06:00 前就出發時警告。
- 已結束的日子顯示「已結束」並收合；完成的日子 `done:true`。
- 旅程期間（用 `{{TZ}}` 的日期）網站直接開在「行程」的今天。

## 6. Claude 讀寫行程（GitHub Actions 橋接）
雲端環境通常連不到 Firebase 與 github.io，所以走 Actions：
- **讀**：`read-firebase.yml`（`path=plan` 或 `all`）把資料放到 `snapshot` 分支，再用 `gh api` 取回。
- **寫**：`write-plan.yml`，輸入 `date`、`expect_ts`、`payload`。先備份到 `snapshot/backup/`，live 的 `ts` 與 `expect_ts` 不同就拒絕，寫完讀回比對。
- 需要 repo secret `FIREBASE_SECRET`，由使用者自己放進 Settings > Secrets，**不要貼到聊天**。
- 用 REST，不用 `gh run` 與 GraphQL（雲端環境會擋）。
- workflow 裡的日期允許範圍要改成 `{{START}}` 到 `{{END}}`，Firebase 網址改成 `{{FB_DB}}`。

## 7. 金鑰與服務
| 項目 | 放哪裡 | 注意 |
|---|---|---|
| Firebase 密鑰 | GitHub Secret `FIREBASE_SECRET`，本機工具讀 `~/.{{PREFIX}}/firebase_secret.txt` | 不 commit、不印出 |
| Google Places 金鑰 | `index.html` 的 `GMAPS_KEY` | 限制只能用 Places API (New)，並限制來源網址 |
| Gemini 金鑰 | Cloudflare Worker Secret `GEMINI_API_KEY` | 不在 repo；換金鑰流程見舊站 README |
| Worker | 手動貼到 Cloudflare 主控台部署 | 改了 `worker/index.js` 要重新部署 |

問 AI 的已知取捨：限流計數是每個 Worker 實例各算各的，不能靠它擋人；偽造來源的人可用光當天免費額度，但拿不到金鑰。要持久限流需用 Cloudflare KV 或 rate-limit binding。拒答語句要改成「我只回答 {{REGION}} 行程相關的問題」。

## 8. 安全修改程序
- 用小型修補腳本，替換精確字串並斷言命中次數；再取出最後一個 `<script>` 區塊，用 `node --check` 檢查。
- 刪程式前列出它定義的所有識別字，grep 確認沒有其他地方在用（曾因刪掉 `ago()` 讓所有行程存檔壞掉）。
- 測試行程修改時，把 `window.fetch` 對 `/plan/` 的寫入換成假的，避免動到真資料。
- Leaflet 要先設定地圖視角，再加圓形標記；畫面外的卡片用 `content-visibility`，讀文字要用 `textContent`。
- `?now=2026-10-16T13:50` 這類參數可預覽旅程中的某個時刻（日期依新旅程調整）。
- commit 訊息依環境指示加上 Claude 的共同作者行。

## 9. 上線前清單
- [ ] 第 1 節欄位全部填完，沒有殘留 `cnx`、`Thailand`、`Bangkok`、`清邁`
- [ ] 新建 Firebase 專案、貼上規則、存到 `firebase-rules.json`
- [ ] 設好 `FIREBASE_SECRET`，用空操作寫入驗證 read／write workflow
- [ ] Google Places 金鑰已限制 API 與來源網址
- [ ] Worker 已部署，問一個問題確認 `X-Model` 標頭
- [ ] `sw.js` 的 `V` 已更新，`SHELL` 清單完整
- [ ] 在手機上測試離線與加到主畫面
- [ ] CLAUDE.md 最後一節「開放項目」已列出待訂項目與未知資訊

## 10. 開放項目（每次旅程自己維護）
- 已訂：
- 待訂：
- 未知資訊（例如回程班次）：
