"""Interactive iOS control server for the Briefly QA harness.

Runs on a GitHub Actions macOS runner next to a booted iOS simulator and exposes
a tiny HTTP API (screenshot / tap / text / swipe / openurl / accessibility tree)
so the driver can interact with the simulator in near-real-time over a tunnel —
instead of the slow write-flow / wait-10min / read-failure batch loop.

Auth: every request must carry `X-Token: <INTERACTIVE_TOKEN>`.
Coordinates: /tap and /swipe accept PIXEL coordinates (the same space as
/screenshot); the server divides by SCALE to get the points idb expects.
"""
import http.server
import json
import os
import socketserver
import subprocess
import urllib.parse

UDID = os.environ.get("UDID", "booted")
TOKEN = os.environ.get("INTERACTIVE_TOKEN", "")
SCALE = float(os.environ.get("SCALE", "3.0"))
PORT = int(os.environ.get("PORT", "8788"))


def run(cmd, timeout=60):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        class R:
            returncode = 124
            stdout = ""
            stderr = f"timeout: {e}"
        return R()


class Handler(http.server.BaseHTTPRequestHandler):
    def _auth(self):
        if TOKEN and self.headers.get("X-Token") != TOKEN:
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"unauthorized")
            return False
        return True

    def _body(self):
        n = int(self.headers.get("Content-Length", "0") or 0)
        if n == 0:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _reply(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _reply_result(self, r):
        self._reply({
            "rc": r.returncode,
            "stdout": (r.stdout or "")[-800:],
            "stderr": (r.stderr or "")[-800:],
        })

    def do_GET(self):
        if not self._auth():
            return
        path = urllib.parse.urlparse(self.path).path
        if path == "/health":
            self._reply({"ok": True, "udid": UDID, "scale": SCALE})
            return
        if path == "/screenshot":
            r = run(["xcrun", "simctl", "io", UDID, "screenshot", "/tmp/shot.png"])
            if r.returncode != 0:
                self._reply({"error": "screenshot failed", "stderr": r.stderr}, 500)
                return
            data = open("/tmp/shot.png", "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/describe":
            # Accessibility tree with element frames (in points) — find any element
            # and tap its center precisely, no coordinate guessing.
            r = run(["idb", "ui", "describe-all", "--udid", UDID])
            self.send_response(200 if r.returncode == 0 else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write((r.stdout or r.stderr or "[]").encode())
            return
        self._reply({"error": "not found"}, 404)

    def do_POST(self):
        if not self._auth():
            return
        path = urllib.parse.urlparse(self.path).path
        b = self._body()
        try:
            if path == "/tap":
                x = float(b["x"]) / SCALE
                y = float(b["y"]) / SCALE
                return self._reply_result(run(["idb", "ui", "tap", "--udid", UDID, str(x), str(y)]))
            if path == "/text":
                return self._reply_result(run(["idb", "ui", "text", "--udid", UDID, str(b["text"])]))
            if path == "/swipe":
                x1 = float(b["x1"]) / SCALE
                y1 = float(b["y1"]) / SCALE
                x2 = float(b["x2"]) / SCALE
                y2 = float(b["y2"]) / SCALE
                dur = str(b.get("duration", 0.3))
                return self._reply_result(run(["idb", "ui", "swipe", "--udid", UDID, "--duration", dur, str(x1), str(y1), str(x2), str(y2)]))
            if path == "/openurl":
                return self._reply_result(run(["xcrun", "simctl", "openurl", UDID, str(b["url"])]))
            if path == "/appearance":
                return self._reply_result(run(["xcrun", "simctl", "ui", UDID, "appearance", str(b.get("value", "light"))]))
            if path == "/button":
                return self._reply_result(run(["idb", "ui", "button", "--udid", UDID, str(b.get("name", "HOME"))]))
        except KeyError as e:
            return self._reply({"error": f"missing field {e}"}, 400)
        except Exception as e:
            return self._reply({"error": str(e)}, 500)
        self._reply({"error": "not found"}, 404)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"[control] listening on 127.0.0.1:{PORT} udid={UDID} scale={SCALE}", flush=True)
        httpd.serve_forever()
