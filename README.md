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

開 <http://localhost:8765/>。Service worker 只在 https 註冊，所以本機不會有離線快取。

## 改版注意

- 改了 `sw.js` 的快取規則或 `SHELL` 清單時，把 `V`（`cnx-v2`）加一號，舊快取才會清掉。
- 新增網站會用到的同網域檔案時，記得加進 `sw.js` 的 `SHELL`，否則第一次離線開啟會缺檔。
