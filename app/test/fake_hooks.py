# Fake Grok Bot webhook receiver for local tests. Records every POST to /tmp/viva-test/hooks.jsonl.
# FAIL_FIRST=N makes the first N requests answer 429 (rate limit), to test retries.
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
LOG = "/tmp/viva-test/hooks.jsonl"
FAIL = {"n": int(os.environ.get("FAIL_FIRST", "0"))}
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()
        code = 429 if FAIL["n"] > 0 else 200
        if FAIL["n"] > 0: FAIL["n"] -= 1
        with open(LOG, "a") as f:
            f.write(json.dumps({"path": self.path, "code": code, "body": json.loads(body or "{}")}) + "\n")
        self.send_response(code); self.end_headers(); self.wfile.write(b"{}")
    def log_message(self, *a): pass
HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
