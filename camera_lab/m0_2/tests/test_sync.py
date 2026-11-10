"""
ROOTS M0.2 backend tests. Run:  python tests/test_sync.py
Starts a real server on a free port with a temporary state folder, then checks
sync latency, command rules, the privacy boundary, persistence and offline-ness.
"""
import json, os, re, socket, subprocess, sys, tempfile, threading, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class Srv:
    def __init__(self, state_dir):
        self.port = free_port()
        env = dict(os.environ, ROOTS_STATE_DIR=str(state_dir))
        self.p = subprocess.Popen([sys.executable, str(ROOT / "server.py"), "--port", str(self.port), "--open", "none"],
                                  env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            try:
                urllib.request.urlopen(self.url("/api/health"), timeout=0.5); break
            except Exception:
                time.sleep(0.1)
        self.token = (Path(state_dir) / ".teacher_token").read_text().strip()

    def url(self, p): return f"http://127.0.0.1:{self.port}{p}"
    def stop(self): self.p.terminate(); self.p.wait(5)

    def cmd(self, action, token=None, **kw):
        req = urllib.request.Request(self.url("/api/command"), json.dumps(dict(action=action, **kw)).encode(),
                                     {"Content-Type": "application/json", "X-Roots-Token": self.token if token is None else token})
        try:
            r = urllib.request.urlopen(req, timeout=3); return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def get(self, path):
        return json.load(urllib.request.urlopen(self.url(path), timeout=3))


class SSE(threading.Thread):
    """Minimal EventSource client; records (arrival_time, payload)."""
    def __init__(self, srv, channel, token=None):
        super().__init__(daemon=True)
        self.events, self.sock = [], socket.create_connection(("127.0.0.1", srv.port))
        q = f"/api/events?channel={channel}" + (f"&token={token}" if token else "")
        self.sock.sendall(f"GET {q} HTTP/1.1\r\nHost: 127.0.0.1:{srv.port}\r\n\r\n".encode())
        self.start()

    def run(self):
        buf = b""
        try:
            while True:
                d = self.sock.recv(65536)
                if not d: return
                buf += d
                while b"\n\n" in buf:
                    chunk, buf = buf.split(b"\n\n", 1)
                    for line in chunk.split(b"\n"):
                        if line.startswith(b"data: "):
                            self.events.append((time.perf_counter(), json.loads(line[6:].decode("utf-8"))))
        except OSError:
            return

    def wait_for(self, pred, timeout=2.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            for t, e in list(self.events):
                if pred(e): return t, e
            time.sleep(0.002)
        return None, None

    def close(self): self.sock.close()


def main():
    tmp = tempfile.mkdtemp()
    srv = Srv(tmp)
    try:
        print("\n== basics ==")
        h = srv.get("/api/health"); check("health endpoint", h.get("app") == "roots-sync")
        st = srv.get("/api/state?channel=public"); check("starts idle", st["phase"] == "idle")
        code, _ = srv.cmd("start_lesson", token="wrong"); check("command without valid token is refused (403)", code == 403)
        try:
            urllib.request.urlopen(srv.url("/api/events?channel=teacher"), timeout=2); ok = False
        except urllib.error.HTTPError as e: ok = e.code == 403
        check("teacher channel needs token", ok)
        req = urllib.request.Request(srv.url("/api/state"), headers={"Host": "evil.example.com"})
        try: urllib.request.urlopen(req, timeout=2); ok = False
        except urllib.error.HTTPError as e: ok = e.code == 403
        check("foreign Host header rejected", ok)
        try: urllib.request.urlopen(srv.url("/../server.py"), timeout=2); ok = False
        except urllib.error.HTTPError: ok = True
        check("path traversal blocked", ok)

        print("\n== live sync (separate connections = separate windows) ==")
        stu, tea = SSE(srv, "public"), SSE(srv, "teacher", srv.token)
        t, e = stu.wait_for(lambda e: True); check("student gets initial snapshot on connect", e is not None)
        t, e = tea.wait_for(lambda e: e["connections"]["public"] == 1)
        check("teacher sees 1 student display connected", e is not None)
        lat = []

        def do(action, pred, **kw):
            t0 = time.perf_counter(); code, r = srv.cmd(action, **kw)
            ta, e = stu.wait_for(lambda e: e["version"] >= r.get("version", 1e9) and pred(e)) if code == 200 else (None, None)
            if code == 200 and ta: lat.append((ta - t0) * 1000)
            return code, e

        c, e = do("start_lesson", lambda e: e["phase"] == "lesson"); check("Start Lesson reaches student display", c == 200 and e and e["slide"]["index"] == 0)
        c, e = do("next", lambda e: e["phase"] == "lesson" and e["slide"]["index"] == 1); check("Next Slide reaches student display", c == 200 and e)
        c, e = do("prev", lambda e: e["phase"] == "lesson" and e["slide"]["index"] == 0); check("Previous Slide reaches student display", c == 200 and e)
        code, r = srv.cmd("prev"); check("Previous on first slide refused", code == 409)
        for _ in range(5): srv.cmd("next")
        code, r = srv.cmd("next"); check("Next past last slide refused (must Start Quiz)", code == 409)
        c, e = do("start_quiz", lambda e: e["phase"] == "quiz"); check("Start Quiz reaches student display", c == 200 and e and e["question"]["index"] == 0)

        print("\n== privacy boundary ==")
        q = e["question"]
        check("answer NOT in public payload before reveal", "correct" not in q and "explanation" not in q)
        raw = json.dumps(e)
        check("no teacher fields on public channel", not any(k in raw for k in ('"notes"', '"answer_key"', '"can"', '"connections"')))
        tt, te = tea.wait_for(lambda x: x["phase"] == "quiz")
        check("teacher payload has the answer key", te and te["answer_key"]["letter"] == "B")
        c, e = do("hint", lambda e: e["phase"] == "quiz" and len(e["question"]["hints"]) == 1); check("Hint 1 reaches student display", c == 200 and e)
        c, e = do("reveal", lambda e: e["phase"] == "quiz" and e["question"]["revealed"]); check("Reveal Answer reaches student display", c == 200 and e)
        check("answer present only after reveal", e["question"]["correct"] == "B" and "1/4" in e["question"]["explanation"])
        code, _ = srv.cmd("reveal"); check("double reveal refused", code == 409)
        code, _ = srv.cmd("hint"); check("hint after reveal refused", code == 409)

        print("\n== full lesson flow + Hindi ==")
        c, e = do("set_language", lambda e: e["lang"] == "hi", lang="hi"); check("Language switch reaches student display", c == 200 and "रोटी" in e["question"]["prompt"])
        for i in range(1, 5):
            code, _ = srv.cmd("next"); check(f"Q{i} -> Next Question allowed after reveal", code == 200)
            code, _ = srv.cmd("next"); check(f"Q{i+1}: Next before reveal refused", code == 409)
            srv.cmd("reveal")
        c, e = do("next", lambda e: e["phase"] == "summary"); check("after last question -> summary", c == 200 and e["summary"]["questions"] == 5)
        c, e = do("end_lesson", lambda e: e["phase"] == "ended"); check("End Lesson reaches student display", c == 200 and e)
        code, _ = srv.cmd("end_lesson"); check("End Lesson twice refused", code == 409)
        code, _ = srv.cmd("bogus"); check("unknown command refused", code == 409)
        c, e = do("start_lesson", lambda e: e["phase"] == "lesson"); check("lesson can be restarted", c == 200 and e["slide"]["index"] == 0)

        print("\n== latency (command POST -> student display event, localhost) ==")
        lat.sort()
        med, mx = lat[len(lat) // 2], lat[-1]
        print(f"        {len(lat)} commands: median {med:.1f} ms, max {mx:.1f} ms")
        check("median sync latency < 100 ms", med < 100, f"{med:.1f} ms")

        print("\n== persistence ==")
        srv.cmd("start_quiz"); srv.cmd("reveal"); v = srv.get("/api/state?channel=public")["version"]
        stu.close(); tea.close(); srv.stop(); srv = Srv(tmp)
        st = srv.get("/api/state?channel=public")
        check("state survives server restart", st["phase"] == "quiz" and st["question"]["revealed"] and st["version"] == v)
        check("teacher token survives restart", srv.token == (Path(tmp) / ".teacher_token").read_text().strip())
    finally:
        srv.stop()

    print("\n== offline: no external URLs in the web files ==")
    bad = []
    for f in (ROOT / "web").rglob("*"):
        if f.suffix in (".html", ".css", ".js"):
            for m in re.finditer(r"https?://[^\s\"')<>]+", f.read_text(encoding="utf-8")):
                if not m.group(0).startswith(("http://www.w3.org/", "http://127.0.0.1", "http://localhost")):
                    bad.append((f.name, m.group(0)))
    check("no external http(s) references in web/", not bad, str(bad))
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
