# Local end-to-end test: 5 approves + 3 adjusts tapped in a row, with some webhooks rate-limited.
# Uses only the local wrangler dev server (fake secrets). Run: python3 test/burst_test.py
import json, subprocess, sys, time, urllib.request, http.cookiejar, concurrent.futures as cf
BASE = "http://localhost:8788"; TOK = "test-bot-token"
LOG = "/tmp/viva-test/hooks.jsonl"
COOKIE = {"v": ""}
op = urllib.request.build_opener()
def req(method, path, body=None, bot=False):
    r = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    r.add_header("Content-Type", "application/json"); r.add_header("x-viva", "1")
    if bot: r.add_header("Authorization", "Bearer " + TOK)
    elif COOKIE["v"]: r.add_header("Cookie", COOKIE["v"])
    try:
        with op.open(r) as res:
            sc = res.headers.get("Set-Cookie")
            if sc: COOKIE["v"] = sc.split(";")[0]
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"{}")
def d1(sql):
    out = subprocess.run(["npx", "wrangler", "d1", "execute", "viva-orders-localtest", "--local", "--persist-to", "/tmp/viva-test/state",
        "-c", "test/wrangler.test.jsonc", "--json", "--command", sql], capture_output=True, text=True, cwd="/workspace/viva-orders")
    return json.loads(out.stdout)[0]["results"]
def sweep():
    with urllib.request.urlopen(BASE + "/__scheduled?cron=*/10+*+*+*+*") as r: r.read()
    time.sleep(1.5)
def hooks():
    try: return [json.loads(l) for l in open(LOG)]
    except FileNotFoundError: return []

def main():
    orders = []
    for i in range(8):
        orders.append({"order_id": f"T{i}", "buyer_first_name": f"Buyer{i}", "status": "Waiting for Derek",
            "artist_bot": "Designer" if i != 7 else "Designer 2",
            "review": {"kind": "art_proof", "version": "v1", "artist_bot": "Designer" if i != 7 else "Designer 2",
                       "options": [{"label": "A", "image": None, "source_path": f"/workspace/orders/T{i}/art/v1/a.png"}]}})
    print("push", req("POST", "/api/bot/push", {"orders": orders}, bot=True))
    print("login", req("POST", "/api/login", {"password": "test-pass"})[0])
    def tap(i):
        body = {"order_id": f"T{i}", "review_key": f"T{i}|art_proof|v1", "action": "approve" if i < 5 else "adjust",
                "option": None, "adjust_text": None if i < 5 else f"change #{i}"}
        return req("POST", "/api/decisions", body)
    # all 8 taps fired together (worst case: faster than Derek can tap)
    with cf.ThreadPoolExecutor(8) as ex: res = list(ex.map(tap, range(8)))
    for i, (code, r) in enumerate(res):
        d = r.get("decision") or {}
        print("tap", i, code, d.get("target_bot"), d.get("webhook_status"), r.get("error"))
    h = hooks(); print("webhooks so far:", len(h), "codes:", [x["code"] for x in h])
    print("first wake for Messanger says pending_for_you =", [x["body"].get("pending_for_you") for x in h if x["path"] == "/Messanger"])
    print("pending (bot view):", len(req("GET", "/api/bot/decisions?status=pending", bot=True)[1]["decisions"]))

if __name__ == '__main__':
    main()
