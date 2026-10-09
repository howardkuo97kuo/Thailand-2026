"""Helper for the 地點庫 inbox agent.

The site's 新增地點 tab writes submissions to Firebase /inbox. A scheduled Claude task runs this script:

  python tools/inbox_agent.py pending              -> claims new submissions, prints Google candidates as JSON
  python tools/inbox_agent.py search "<query>"       -> more candidates when pending's look wrong (e.g. Thai name)
  python tools/inbox_agent.py add <decision.json>  -> writes the chosen place to /places and marks the item 已加入
  python tools/inbox_agent.py dup <inboxId> <placeId>
  python tools/inbox_agent.py fail <inboxId> "<reason shown to people>"

Writing needs the Firebase database secret in %USERPROFILE%\\.cnx\\firebase_secret.txt (never commit it).
The Google key is read from index.html; requests send the site's allowed Referer.
"""
import io, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FB = "https://thailand-2026-7304d-default-rtdb.asia-southeast1.firebasedatabase.app"
REFERER = "http://localhost:8765/"
CATS = ["景點", "美食", "咖啡甜點", "按摩", "課程體驗", "購物市集", "其他"]
REGIONS = ["古城", "古城東・塔佩門", "夜市・濱河", "尼曼", "北區", "西郊", "城南", "郊區"]
WD = "日一二三四五六"
GOOGLE_DAY = [1, 2, 3, 4, 5, 6, 0]  # weekdayDescriptions are Monday-first; convert to Sunday=0


def secret():
    p = os.path.join(os.path.expanduser("~"), ".cnx", "firebase_secret.txt")
    try:
        return io.open(p, encoding="utf-8").read().strip()
    except OSError:
        sys.exit(f"Missing Firebase secret file: {p}")


def gkey():
    s = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r'const GMAPS_KEY="([^"]+)"', s)
    return m.group(1), s


def fb(path, method="GET", data=None):
    url = f"{FB}/{path}.json?auth={urllib.parse.quote(secret())}"
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8") or "null")


def google(url, body=None, mask=None):
    key, _ = gkey()
    headers = {"Referer": REFERER, "X-Goog-Api-Key": key}
    if body is not None:
        headers["Content-Type"] = "application/json"
        headers["X-Goog-FieldMask"] = mask
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    else:
        req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


DETAIL_FIELDS = ("id,displayName,formattedAddress,shortFormattedAddress,location,rating,userRatingCount,businessStatus,"
                 "primaryTypeDisplayName,types,regularOpeningHours,priceRange,paymentOptions,reservable,reviews,editorialSummary")


def details(pid, lang="zh-TW"):
    return google(f"https://places.googleapis.com/v1/places/{pid}?fields={DETAIL_FIELDS}&languageCode={lang}")


def query_from_text(text):
    """Plain names get ' Chiang Mai' appended; Google Maps links are expanded to the place name in the URL."""
    url = re.search(r"https?://\S+", text)
    if url:
        try:
            req = urllib.request.Request(url.group(0), headers={"User-Agent": "Mozilla/5.0"})
            final = urllib.request.urlopen(req, timeout=20).geturl()
            m = re.search(r"/place/([^/@?]+)", final)
            if m:
                return urllib.parse.unquote_plus(m.group(1)) + " Chiang Mai"
            m = re.search(r"[?&]q=([^&]+)", final)
            if m:
                return urllib.parse.unquote_plus(m.group(1))
        except Exception:
            pass
        text = text.replace(url.group(0), " ").strip() or url.group(0)
    return text if re.search(r"chiang\s*mai|清邁|เชียงใหม่", text, re.I) else text + " Chiang Mai"


def search(q):
    mask = "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.businessStatus,places.primaryTypeDisplayName"
    body = {"textQuery": q, "maxResultCount": 3, "languageCode": "zh-TW",
            "locationBias": {"circle": {"center": {"latitude": 18.7883, "longitude": 98.9853}, "radius": 40000.0}}}
    return google("https://places.googleapis.com/v1/places:searchText", body, mask).get("places", [])


def known_pids():
    _, s = gkey()
    pids = {v: k for k, v in re.findall(r'\{id:"([^"]+)",[^\n]*?pid:"([^"]+)"', s)}
    added = fb("places") or {}
    for pid_, p in added.items():
        if isinstance(p, dict) and p.get("pid"):
            pids[p["pid"]] = p.get("id", pid_)
    ids = set(re.findall(r'\{id:"([^"]+)",', s)) | set(added.keys())
    return pids, ids


def candidates(q, pids):
    cands = []
    for c in search(q):
        d = details(c["id"])
        revs = [((r.get("originalText") or r.get("text") or {}).get("text", "")).replace("\n", " ")[:300] for r in (d.get("reviews") or [])[:5]]
        cands.append({
            "pid": d["id"], "name": d.get("displayName", {}).get("text"), "address": d.get("formattedAddress"),
            "rating": d.get("rating"), "reviews_count": d.get("userRatingCount"), "status": d.get("businessStatus"),
            "type": (d.get("primaryTypeDisplayName") or {}).get("text"),
            "hours": (d.get("regularOpeningHours") or {}).get("weekdayDescriptions"),
            "price": d.get("priceRange"), "payment": d.get("paymentOptions"), "reservable": d.get("reservable"),
            "summary": (d.get("editorialSummary") or {}).get("text"), "reviews": revs,
            "already_in_site_as": pids.get(d["id"]),
        })
    return cands


def cmd_search(q):
    """Try another query (e.g. the Thai or Chinese name) when pending's candidates look wrong or thin."""
    pids, _ = known_pids()
    print(json.dumps({"query": q, "candidates": candidates(q, pids)}, ensure_ascii=False, indent=1))


def cmd_pending():
    inbox = fb("inbox") or {}
    pids, _ = known_pids()
    now = int(time.time() * 1000)
    out = []
    for iid, it in sorted(inbox.items(), key=lambda kv: (kv[1] or {}).get("ts", 0)):
        if not isinstance(it, dict):
            continue
        stale = it.get("status") == "processing" and now - it.get("claimedAt", 0) > 3600_000
        if it.get("status") != "new" and not stale:
            continue
        fb(f"inbox/{iid}", "PATCH", {"status": "processing", "claimedAt": now})
        q = query_from_text(it.get("text", ""))
        cands = candidates(q, pids)
        out.append({"inboxId": iid, "text": it.get("text"), "note": it.get("note", ""), "who": it.get("who"), "query": q, "candidates": cands})
    print(json.dumps({"categories": CATS, "regions": REGIONS, "items": out}, ensure_ascii=False, indent=1))


def hours_text(oh):
    desc = (oh or {}).get("weekdayDescriptions") or []
    if not desc:
        return "", []
    days = []
    for i, t in enumerate(desc):
        val = t.split(": ", 1)[1] if ": " in t else t
        days.append((GOOGLE_DAY[i], val.replace(" – ", "–").replace(" ", "")))
    closed = sorted(d for d, v in days if "休息" in v)
    open_vals = [v for d, v in days if "休息" not in v]
    common = max(set(open_vals), key=open_vals.count) if open_vals else ""
    if closed and len(closed) >= 4:
        return f"只有週{'、'.join(WD[d] for d in range(7) if d not in closed)} {common}", closed
    return common + (f"，週{'、'.join(WD[d] for d in closed)}休" if closed else ""), closed


def weekly(oh):
    per = (oh or {}).get("periods") or []
    if len(per) == 1 and "close" not in per[0]:
        return "24h"
    r = []
    for x in per:
        if "open" not in x or "close" not in x:
            continue
        a = x["open"]["day"] * 1440 + x["open"].get("hour", 0) * 60 + x["open"].get("minute", 0)
        b = x["close"]["day"] * 1440 + x["close"].get("hour", 0) * 60 + x["close"].get("minute", 0)
        if b <= a:
            b += 10080
        r.append([a, b])
    return r or None


def short_addr(d):
    a = d.get("shortFormattedAddress") or d.get("formattedAddress") or ""
    a = re.sub(r"^[23456789CFGHJMPQRVWX]{4,8}\+[23456789CFGHJMPQRVWX]{2,3},?\s*", "", a)  # leading plus code
    a = re.sub(r"^[^,\d]*Thailand,\s*", "", a)  # some listings prefix the address with "<name> Chiang Mai Thailand,"
    return re.split(r",?\s*(Tambon|Amphoe|Chang Wat|ตำบล|อำเภอ)\b", a)[0].strip(" ,")


def cmd_add(path):
    dec = json.load(io.open(path, encoding="utf-8"))
    inbox = fb(f"inbox/{dec['inboxId']}") or {}
    assert dec["c"] in CATS, f"category must be one of {CATS}"
    assert dec["r"] in REGIONS, f"region must be one of {REGIONS}"
    pids, ids = known_pids()
    if dec["pid"] in pids:
        return cmd_dup(dec["inboxId"], pids[dec["pid"]])
    pid_id = re.sub(r"[^a-z0-9]", "", dec["id"].lower())[:24] or "place"
    base, n = pid_id, 2
    while pid_id in ids:
        pid_id, n = f"{base}{n}", n + 1
    d = details(dec["pid"])
    h, closed = hours_text(d.get("regularOpeningHours"))
    oh = weekly(d.get("regularOpeningHours"))
    who = inbox.get("who") or ""
    name = {"charlie": "Charlie", "howard": "Howard", "lindsay": "Lindsay"}.get(who, who)
    user_note = (inbox.get("note") or "").strip()
    place = {
        "id": pid_id, "n": dec["n"], "c": dec["c"], "r": dec["r"], "a": short_addr(d), "h": dec.get("h") or h,
        "rt": f'{d["rating"]:.1f}' if d.get("rating") else "", "rv": f'{d["userRatingCount"]:,}' if d.get("userRatingCount") else "",
        "note": f"{name} 提供" + (f"：{user_note}" if user_note else ""), "src": "清單", "pid": d["id"],
        "tip": dec["tip"], "ll": [round(d["location"]["latitude"], 6), round(d["location"]["longitude"], 6)],
        "by": who, "addedAt": int(time.time() * 1000),
    }
    if dec.get("sub"):
        place["sub"] = dec["sub"]
    if dec.get("loc"):
        place["loc"] = dec["loc"]
    if closed:
        place["cd"] = closed
    if oh:
        place["oh"] = oh
    fb(f"places/{pid_id}", "PUT", place)
    fb(f"inbox/{dec['inboxId']}", "PATCH", {"status": "added", "placeId": pid_id, "msg": ""})
    print(json.dumps({"added": pid_id, "name": dec["n"]}, ensure_ascii=False))


def cmd_dup(iid, place_id):
    fb(f"inbox/{iid}", "PATCH", {"status": "duplicate", "placeId": place_id, "msg": "這個地點已經在地點庫裡了"})
    print(json.dumps({"duplicate": place_id}, ensure_ascii=False))


def cmd_fail(iid, msg):
    fb(f"inbox/{iid}", "PATCH", {"status": "failed", "msg": msg[:120]})
    print(json.dumps({"failed": iid}, ensure_ascii=False))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    {"pending": lambda: cmd_pending(), "search": lambda: cmd_search(a[1]), "add": lambda: cmd_add(a[1]), "dup": lambda: cmd_dup(a[1], a[2]),
     "fail": lambda: cmd_fail(a[1], a[2])}[a[0]]()
