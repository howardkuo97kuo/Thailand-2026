"""Shared by the scheduled agents (inbox_agent.py, feedback_agent.py): Firebase access and the site's places.json.

Writing needs the Firebase database secret in %USERPROFILE%\\.cnx\\firebase_secret.txt (never commit or print it).
"""
import io, json, os, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FB = "https://thailand-2026-7304d-default-rtdb.asia-southeast1.firebasedatabase.app"


def secret():
    p = os.path.join(os.path.expanduser("~"), ".cnx", "firebase_secret.txt")
    try:
        return io.open(p, encoding="utf-8").read().strip()
    except OSError:
        sys.exit(f"Missing Firebase secret file: {p}")


def fb(path, method="GET", data=None):
    url = f"{FB}/{path}.json?auth={urllib.parse.quote(secret())}"
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8") or "null")


def site_data():
    """places.json: {"cats": [...], "regions": [...], "places": [...]} — the same file the page loads."""
    return json.load(io.open(os.path.join(ROOT, "places.json"), encoding="utf-8"))
