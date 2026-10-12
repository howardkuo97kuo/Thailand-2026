"""Helper for the nightly 意見 (feedback) run.

People write suggestions on the site's 意見 tab; each lands in Firebase /feedback with status "new".
Every night a scheduled Claude task runs this script:

  python tools/feedback_agent.py list                    -> JSON of items to handle: status "approved" (do them) and "new" (propose)
  python tools/feedback_agent.py propose <id> <file>     -> store the proposal text (UTF-8 file) and set status "proposed"
  python tools/feedback_agent.py done <id> <file>        -> store what was changed (UTF-8 file) and set status "done"
  python tools/feedback_agent.py fail <id> "<reason>"    -> set status "failed" with a short reason shown on the site

Only Howard can approve a proposal on the site (status "approved"); nothing is changed before that.
Firebase access and the secret file are in cnx_common.py.
"""
import io, json, sys, time

from cnx_common import fb


def read_text(path):
    return io.open(path, encoding="utf-8").read().strip()


def cmd_list():
    items = fb("feedback") or {}
    out = {"approved": [], "new": []}
    for fid, it in sorted(items.items(), key=lambda kv: (kv[1] or {}).get("ts", 0)):
        if not isinstance(it, dict):
            continue
        st = it.get("status")
        if st in out:
            out[st].append({"id": fid, "who": it.get("who"), "text": it.get("text"), "proposal": it.get("proposal", ""),
                            "ts": it.get("ts")})
    print(json.dumps(out, ensure_ascii=False, indent=1))


def cmd_propose(fid, path):
    text = read_text(path)
    assert text, "empty proposal"
    fb(f"feedback/{fid}", "PATCH", {"status": "proposed", "proposal": text[:2000], "proposedAt": int(time.time() * 1000)})
    print(json.dumps({"proposed": fid}, ensure_ascii=False))


def cmd_done(fid, path):
    text = read_text(path)
    fb(f"feedback/{fid}", "PATCH", {"status": "done", "result": text[:2000], "doneAt": int(time.time() * 1000)})
    print(json.dumps({"done": fid}, ensure_ascii=False))


def cmd_fail(fid, msg):
    fb(f"feedback/{fid}", "PATCH", {"status": "failed", "result": msg[:300], "doneAt": int(time.time() * 1000)})
    print(json.dumps({"failed": fid}, ensure_ascii=False))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    {"list": lambda: cmd_list(), "propose": lambda: cmd_propose(a[1], a[2]), "done": lambda: cmd_done(a[1], a[2]),
     "fail": lambda: cmd_fail(a[1], a[2])}[a[0]]()
