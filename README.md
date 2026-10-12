# 清邁員旅地點庫

2026/10/15–10/20 清邁員旅的候選地點、行程與已訂項目。
網站：<https://howardkuo97kuo.github.io/Thailand-2026/>（GitHub Pages，直接發佈 `main` 分支）。

沒有建置步驟：改完檔案、推上 `main` 就上線。

## 檔案

| 檔案 | 內容 |
| --- | --- |
| `index.html` | 整個網站（樣式、版面、程式），以及行程 `PLAN`、住宿 `LODGING`、訂位等資料 |
| `places.json` | 分類 `cats`、地區 `regions`、內建地點 `places`；網頁與 inbox agent 讀同一份 |
| `sw.js` | 離線支援：頁面、函式庫、上次看到的資料、照片與地圖圖磚都存在裝置上 |
| `manifest.webmanifest`、`icon-*.png`、`og.png` | 加到主畫面與分享預覽用 |
| `worker/index.js` | 「問 AI」的後端（Cloudflare Worker），整個檔案貼到 Cloudflare 主控台部署 |
| `tools/inbox_agent.py` | 處理「新地點推薦」分頁送出的地點 |
| `tools/feedback_agent.py` | 處理「意見」分頁的建議 |
| `tools/cnx_common.py` | 兩支工具共用：Firebase 讀寫、讀 `places.json` |

## 地點資料

`places.json` 的 `places` 一行一個地點，欄位：

- `id`、`n` 名稱、`loc` 中文說明（選填）、`c` 分類、`sub` 小分類（選填）、`r` 地區、`a` 地址
- `h` 營業時間文字、`cd` 公休的星期（0 = 週日）、`oh` 每週營業時段（從週日 00:00 起算的分鐘）
- `rt` 評分、`rv` 評論數、`pid` Google Place ID、`ll` 經緯度
- `note` 我們的備註、`tip` 小提醒、`src` 來源（`清單` = 團隊挑的，`建議` = AI 建議）
- `m` Charlie 的預設愛心

`c` 為 `其他` 的地點（換匯等）不會出現在「挑地點」，只列在「已訂」分頁。

大家在網站上推薦的地點不在這個檔案裡，而是存在 Firebase `/places`，網頁載入後才合併進來。

## Firebase（Realtime Database）

網頁不登入，直接用 REST 讀寫；能做什麼由資料庫規則決定。

| 路徑 | 用途 |
| --- | --- |
| `/must`、`/hearts/howard`、`/hearts/lindsay` | 三個人的愛心（Charlie 沿用舊的 `/must`） |
| `/plan` | 可編輯的每日行程 |
| `/inbox` | 推薦地點的收件匣 |
| `/places`、`/removed` | agent 加進來的地點、被移除的地點 |
| `/feedback` | 意見與 AI 的建議、Howard 的決定 |

規則沒有放在這個 repo，要到 Firebase 主控台看。網頁上「只有 Howard 能同意執行」目前只是前端檢查，
真正的限制要寫在 `/feedback` 的規則裡。

## 問 AI

右下角的「問 AI」讓大家用中文問行程。網頁把問題和一份網站資料的文字摘要（`chatContext()`，上限 30,000 字）
送給 Cloudflare Worker，Worker 加上規則和金鑰後呼叫 Gemini，再把答案逐字傳回來。

| 項目 | 內容 |
| --- | --- |
| Worker 名稱 | `cnx-chat` |
| 網址 | `https://cnx-chat.howardkuo97.workers.dev` |
| 原始碼 | `worker/index.js` |
| 金鑰 | Worker 的 Secret `GEMINI_API_KEY`（Cloudflare → Settings → Variables and Secrets）；不在 repo，也不在網頁裡 |
| 允許的來源 | `https://howardkuo97kuo.github.io`、`http://localhost:8765` |

限制：每次 1–12 則訊息、每則最多 500 字（網頁重送舊訊息時會截到 500 字）、網站資料最多 30,000 字；
Worker 裡寫了每個 IP 每分鐘 10 次，但計數是每個 Worker 實例各算各的，實測連續 11 次請求都過了，所以不能靠它擋人。
真正的上限只有 Gemini 免費層的每日額度（全部模型合計約 1,060 次回答）。偽造 `Origin` 標頭的人可以用光當天的額度，
也能自己帶任意的網站資料，等於把這個 Worker 當成用這把金鑰的 Gemini 代理；但他們讀不到金鑰，也不會產生費用（沒有綁付款方式）。
要有持久的限流，得用 Cloudflare KV 或 rate-limit binding。問清邁以外的事，固定回「這個我幫不上忙，我只回答清邁行程相關的問題。」

改了 `worker/index.js` 之後要手動重新部署（這台電腦沒有 Node.js，不用 wrangler）：
Cloudflare 主控台 → Workers & Pages → `cnx-chat` → Edit code → 貼上整個檔案 → Deploy。
網頁不用跟著改，除非 Worker 網址變了（`index.html` 的 `CHAT_URL`）。
部署後到網站問一個問題確認：瀏覽器開發者工具 → Network，回應標頭 `X-Model` 會顯示是哪個模型回答的。

**換金鑰。** 到 Google AI Studio 建一把新金鑰 → 在 Cloudflare 的 Settings → Variables and Secrets 把 `GEMINI_API_KEY`
改成新的並 Deploy → 回 AI Studio 刪掉舊金鑰 → 到網站問一個問題確認還答得出來。

**模型。** Worker 依序試 `MODELS` 裡的模型，遇到過載、額度用完或被拒絕就換下一個：
`gemini-3.5-flash-lite`、`gemini-3.1-flash-lite`、`gemini-3.8-flash`、`gemini-3.6-flash`、`gemini-3-flash-preview`。
免費層的額度（2026/10/12 在 Google AI Studio 看到的）：

| 模型 | 每分鐘 | 每天 |
| --- | --- | --- |
| 兩個 Flash-Lite | 15 次 | 各 500 次 |
| 所有 Flash | 5 次 | 20 次 |

所以 Flash-Lite 排前面。額度和型號會變，要換就改 `MODELS`。免費層的對話內容 Google 可能用來改進產品。

**搜尋。** Worker 裡 `SEARCH = false`：3.x 模型的 Google 搜尋沒有免費額度，所以關著。網站上沒有的清邁問題，
AI 憑自己的知識回答，並註明不是網站資料、可能不是最新的，答案沒有來源連結。要開搜尋與來源連結，
先在 Google AI Studio 開啟計費，再把 `SEARCH` 改成 `true` 並重新部署。

**額度用完時，使用者看到：**

| 狀況 | 訊息 |
| --- | --- |
| 離線 | 需要網路才能問。 |
| 每分鐘上限 | 問得有點快，等一下再試。 |
| 每個模型的當天額度都用完 | 今天的免費額度用完了，明天再問。 |
| 其他任何錯誤 | 現在連不上，稍後再試。 |

**問了沒反應時。** 瀏覽器開發者工具 → Network，看 `cnx-chat` 那筆請求的回應：錯誤內容裡的 `status` 和
`detail` 會寫是哪個模型、為什麼失敗（`no_key` 表示 Secret 沒設）。

## 排程工具

兩支工具都由排程的 Claude 任務執行，用法寫在各檔案開頭：

- `inbox_agent.py`：約每 30 分鐘，把 `/inbox` 的新項目查好 Google 資料後寫進 `/places`。
- `feedback_agent.py`：每晚 11 點，把新意見整理成建議；Howard 同意後，下一次才真的修改。

需要：

- Python 3（只用標準函式庫）。
- Firebase 資料庫密鑰放在 `%USERPROFILE%\.cnx\firebase_secret.txt`。**不要 commit，也不要印出來。**
- Google Places API 金鑰寫在 `index.html` 的 `GMAPS_KEY`，工具從那裡讀取。金鑰在 Google Cloud 要限制只能用
  Places API (New)，並限制來源網址。

## 本機預覽

```
python -m http.server 8765
```

開 <http://localhost:8765/>。Service worker 只在 https 註冊，所以本機不會有離線快取。「問 AI」在本機也能用，因為 Worker 允許這個來源。

## 改版注意

- 改了 `sw.js` 的快取規則或 `SHELL` 清單時，把 `V`（`cnx-v2`）加一號，舊快取才會清掉。
- 新增網站會用到的同網域檔案時，記得加進 `sw.js` 的 `SHELL`，否則第一次離線開啟會缺檔。
