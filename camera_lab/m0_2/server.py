#!/usr/bin/env python3
"""
ROOTS M0.2 - local classroom sync server.  Python standard library only (no pip install).

One laptop, two browser pages:
    /teacher  -> controls the lesson (sends commands)
    /student  -> shows the classroom display (receives state)
The server owns the single lesson state. Every state change is pushed to all open
pages instantly over Server-Sent Events (SSE). Binds to 127.0.0.1 only.

PRIVACY BOUNDARY: the 'public' channel (student display) is built by public_view(),
which never includes the answer key (until Reveal), teacher notes, or any student data.

    python server.py [--port 8765] [--open home|split|teacher|student|none]
"""
import argparse, json, os, queue, secrets, sys, threading, time, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
WEB, DATA = ROOT / "web", ROOT / "data"
LESSON_FILE = DATA / "lessons" / "fractions_c5.json"
STATE_DIR = Path(os.environ.get("ROOTS_STATE_DIR", DATA))      # tests point this at a temp folder
STATE_FILE, TOKEN_FILE = STATE_DIR / "live_state.json", STATE_DIR / ".teacher_token"
HOST, DEFAULT_PORT = "127.0.0.1", 8765
LETTERS = "ABCD"
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml", ".woff2": "font/woff2", ".png": "image/png", ".ico": "image/x-icon",
        ".txt": "text/plain; charset=utf-8"}


def tr(v, lang):
    if isinstance(v, dict):
        return v.get(lang) or v.get("en") or ""
    return "" if v is None else v


def trlist(v, lang):
    if isinstance(v, dict):
        return v.get(lang) or v.get("en") or []
    return v or []


class Engine:
    """Authoritative lesson state machine + live broadcast hub."""

    def __init__(self, lesson):
        self.lesson = lesson
        self.lock = threading.RLock()
        self.subs = {"public": set(), "teacher": set()}
        self.state = self._load() or self._fresh()

    # ---------- state ----------
    def _fresh(self):
        return {"version": 0, "lesson_id": self.lesson["id"], "lang": "en", "phase": "idle",
                "slide": 0, "q": 0, "revealed": False, "hints": 0, "updated_at": time.time()}

    def _load(self):
        try:
            s = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            ns, nq = len(self.lesson["slides"]), len(self.lesson["questions"])
            ok = (s["phase"] in ("idle", "lesson", "quiz", "summary", "ended") and s["lang"] in ("en", "hi")
                  and 0 <= s["slide"] < ns and 0 <= s["q"] < nq and s["lesson_id"] == self.lesson["id"])
            return s if ok else None
        except Exception:
            return None

    def _save(self):
        try:
            tmp = STATE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.state), encoding="utf-8")
            os.replace(tmp, STATE_FILE)
        except OSError as e:
            print("  (could not save state:", e, ")")

    # ---------- views ----------
    def _tree_stage(self):
        s, ns, nq = self.state, len(self.lesson["slides"]), len(self.lesson["questions"])
        if s["phase"] in ("summary",):
            return 3
        if s["phase"] == "lesson":
            done = s["slide"]
        elif s["phase"] == "quiz":
            done = ns + s["q"] + (1 if s["revealed"] else 0)
        else:
            return 0
        f = done / (ns + nq)
        return 0 if f < 0.15 else 1 if f < 0.5 else 2 if f < 0.85 else 3

    def can(self):
        s, ns, nq = self.state, len(self.lesson["slides"]), len(self.lesson["questions"])
        ph = s["phase"]
        nh = len(self.lesson["questions"][s["q"]]["hints"])
        return {
            "start_lesson": ph in ("idle", "ended", "summary"),
            "prev": (ph == "lesson" and s["slide"] > 0) or ph == "quiz",
            "next": (ph == "lesson" and s["slide"] < ns - 1) or (ph == "quiz" and s["revealed"]),
            "start_quiz": ph == "lesson",
            "reveal": ph == "quiz" and not s["revealed"],
            "hint": ph == "quiz" and not s["revealed"] and s["hints"] < nh,
            "end_lesson": ph in ("lesson", "quiz", "summary"),
            "reset": ph in ("ended", "summary"),
        }

    def view(self, channel):
        """Build the payload for a channel. 'public' is the projector-safe view."""
        s, L, lang = self.state, self.lesson, self.state["lang"]
        slides, qs, ph = L["slides"], L["questions"], self.state["phase"]
        ns, nq = len(slides), len(qs)
        out = {"version": s["version"], "phase": ph, "lang": lang,
               "lesson": {"title": tr(L["title"], lang), "subtitle": tr(L.get("subtitle"), lang),
                          "slides": ns, "questions": nq},
               "tree_stage": self._tree_stage()}
        path = []
        for i in range(ns):
            st = ("done" if ph in ("quiz", "summary") or (ph == "lesson" and i < s["slide"])
                  else "current" if ph == "lesson" and i == s["slide"] else "todo")
            path.append({"kind": "slide", "state": st})
        for j in range(nq):
            if ph == "summary":
                st = "done"
            elif ph == "quiz":
                st = ("done" if j < s["q"] or (j == s["q"] and s["revealed"])
                      else "current" if j == s["q"] else "todo")
            else:
                st = "todo"
            path.append({"kind": "quiz", "state": st})
        out["path"] = path
        if ph == "lesson":
            sl = slides[s["slide"]]
            out["slide"] = {"index": s["slide"], "total": ns, "title": tr(sl["title"], lang),
                            "body": trlist(sl["body"], lang), "visual": sl.get("visual"),
                            "mood": sl.get("mood", "happy"), "accent": s["slide"] % 5}
        if ph == "quiz":
            q = qs[s["q"]]
            qq = {"index": s["q"], "total": nq, "prompt": tr(q["prompt"], lang), "visual": q.get("visual"),
                  "options": [{"letter": LETTERS[i], "text": tr(o, lang)} for i, o in enumerate(q["options"])],
                  "hints": [tr(h, lang) for h in q["hints"][:s["hints"]]], "revealed": s["revealed"]}
            if s["revealed"]:                       # the answer leaves the server only at Reveal
                qq["correct"] = LETTERS[q["correct"]]
                qq["explanation"] = tr(q["explanation"], lang)
            out["question"] = qq
        if ph == "summary":
            out["summary"] = {"slides": ns, "questions": nq}
        if channel == "teacher":
            out["can"] = self.can()
            out["slide_titles"] = [tr(x["title"], lang) for x in slides]
            out["connections"] = {k: len(v) for k, v in self.subs.items()}
            if ph == "lesson":
                out["notes"] = tr(slides[s["slide"]].get("notes"), lang)
            if ph == "quiz":
                q = qs[s["q"]]
                out["answer_key"] = {"letter": LETTERS[q["correct"]], "text": tr(q["options"][q["correct"]], lang),
                                     "hint_total": len(q["hints"])}
        return out

    # ---------- pub/sub ----------
    def subscribe(self, channel):
        q = queue.Queue(maxsize=50)
        with self.lock:
            self.subs[channel].add(q)
            q.put(json.dumps(self.view(channel), ensure_ascii=False))
            self._push("teacher")            # presence changed
        return q

    def unsubscribe(self, channel, q):
        with self.lock:
            self.subs[channel].discard(q)
            self._push("teacher")

    def _push(self, channel):
        if not self.subs[channel]:
            return
        msg = json.dumps(self.view(channel), ensure_ascii=False)
        for q in list(self.subs[channel]):
            try:
                q.put_nowait(msg)
            except queue.Full:                # every message is a full snapshot: drop the oldest
                try:
                    q.get_nowait(); q.put_nowait(msg)
                except Exception:
                    pass

    # ---------- commands ----------
    def command(self, action, args):
        with self.lock:
            s, L = self.state, self.lesson
            ns, nq, ph = len(L["slides"]), len(L["questions"]), s["phase"]
            err = None
            if action == "start_lesson":
                if ph in ("lesson", "quiz"):
                    err = "A lesson is already running. End it first."
                else:
                    s.update(phase="lesson", slide=0, q=0, revealed=False, hints=0)
            elif action == "prev":
                if ph == "lesson":
                    if s["slide"] == 0: err = "This is the first slide."
                    else: s["slide"] -= 1
                elif ph == "quiz":
                    if s["q"] > 0: s.update(q=s["q"] - 1, revealed=True, hints=0)
                    else: s.update(phase="lesson", slide=ns - 1, revealed=False, hints=0)
                else:
                    err = "Nothing to go back to."
            elif action == "next":
                if ph == "lesson":
                    if s["slide"] < ns - 1: s["slide"] += 1
                    else: err = "That was the last slide. Press Start Quiz."
                elif ph == "quiz":
                    if not s["revealed"]: err = "Reveal the answer first."
                    elif s["q"] < nq - 1: s.update(q=s["q"] + 1, revealed=False, hints=0)
                    else: s["phase"] = "summary"
                else:
                    err = "Start the lesson first."
            elif action == "goto":
                i = args.get("index")
                if ph != "lesson": err = "You can jump between slides during the lesson."
                elif not isinstance(i, int) or not 0 <= i < ns: err = "No such slide."
                else: s["slide"] = i
            elif action == "start_quiz":
                if ph != "lesson": err = "Start the lesson first."
                else: s.update(phase="quiz", q=0, revealed=False, hints=0)
            elif action == "reveal":
                if ph != "quiz": err = "There is no question on screen."
                elif s["revealed"]: err = "The answer is already shown."
                else: s["revealed"] = True
            elif action == "hint":
                nh = len(L["questions"][s["q"]]["hints"]) if ph == "quiz" else 0
                if ph != "quiz" or s["revealed"]: err = "Hints are available while a question is open."
                elif s["hints"] >= nh: err = "No more hints for this question."
                else: s["hints"] += 1
            elif action == "end_lesson":
                if ph in ("idle", "ended"): err = "No lesson is running."
                else: s.update(phase="ended", revealed=False, hints=0)
            elif action == "reset":
                if ph in ("ended", "summary"): s.update(phase="idle", slide=0, q=0, revealed=False, hints=0)
                else: err = "Nothing to reset."
            elif action == "set_language":
                lang = args.get("lang")
                if lang not in ("en", "hi"): err = "Language must be en or hi."
                else: s["lang"] = lang
            else:
                err = f"Unknown command: {action}"
            if err:
                return False, err
            s["version"] += 1
            s["updated_at"] = time.time()
            self._save()
            self._push("public")
            self._push("teacher")
            return True, None


def token():
    try:
        t = TOKEN_FILE.read_text().strip()
        if len(t) >= 16:
            return t
    except OSError:
        pass
    t = secrets.token_urlsafe(18)
    TOKEN_FILE.write_text(t)
    return t


class Handler(BaseHTTPRequestHandler):
    engine: Engine = None
    token: str = ""
    disable_nagle_algorithm = True

    def log_message(self, *a):
        pass

    # ----- helpers -----
    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _host_ok(self):
        return self.headers.get("Host", "").split(":")[0] in ("127.0.0.1", "localhost")

    def _teacher_ok(self, supplied):
        return bool(supplied) and secrets.compare_digest(supplied, self.token)

    # ----- GET -----
    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"ok": False, "error": "bad host"})
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        p = u.path
        try:
            if p == "/api/health":
                return self._json(200, {"app": "roots-sync", "ok": True})
            if p in ("/api/state", "/api/events"):
                ch = (qs.get("channel") or ["public"])[0]
                if ch not in ("public", "teacher"):
                    return self._json(400, {"ok": False, "error": "bad channel"})
                if ch == "teacher" and not self._teacher_ok((qs.get("token") or [""])[0]):
                    return self._json(403, {"ok": False, "error": "teacher token required"})
                if p == "/api/state":
                    with self.engine.lock:
                        return self._json(200, self.engine.view(ch))
                return self._sse(ch)
            pages = {"/": "index.html", "/teacher": "teacher.html", "/student": "student.html", "/split": "split.html"}
            rel = pages.get(p, p.lstrip("/"))
            f = (WEB / rel).resolve()
            if WEB.resolve() not in f.parents or not f.is_file():
                return self._json(404, {"ok": False, "error": "not found"})
            data = f.read_bytes()
            if rel == "teacher.html":
                data = data.replace(b"__TEACHER_TOKEN__", self.token.encode())
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(f.suffix.lower(), "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionError, OSError):
            pass

    def _sse(self, channel):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = self.engine.subscribe(channel)
        try:
            self.wfile.write(b"retry: 1000\n\n")
            while True:
                try:
                    msg = q.get(timeout=10)
                    self.wfile.write(b"data: " + msg.encode("utf-8") + b"\n\n")
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except OSError:                              # includes BrokenPipe / ConnectionAborted (Windows)
            pass
        finally:
            self.engine.unsubscribe(channel, q)

    # ----- POST -----
    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"ok": False, "error": "bad host"})
        if urlparse(self.path).path != "/api/command":
            return self._json(404, {"ok": False, "error": "not found"})
        if not self._teacher_ok(self.headers.get("X-Roots-Token", "")):
            return self._json(403, {"ok": False, "error": "Teacher token missing or old. Reload the teacher page."})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 10_000:
                raise ValueError
            body = json.loads(self.rfile.read(n) or b"{}")
            action = str(body.get("action", ""))
        except Exception:
            return self._json(400, {"ok": False, "error": "bad request"})
        ok, err = self.engine.command(action, body)
        print(f"  [{time.strftime('%H:%M:%S')}] teacher: {action}" + ("" if ok else f"  (refused: {err})"))
        self._json(200 if ok else 409, {"ok": ok, "error": err, "version": self.engine.state["version"]})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    # Windows: SO_REUSEADDR would let two servers share one port, so keep it off there. Elsewhere it is needed for fast restarts.
    allow_reuse_address = os.name != "nt"


def open_browser(port, where):
    paths = {"home": "/", "split": "/split", "teacher": "/teacher", "student": "/student"}
    if where in paths:
        threading.Timer(0.6, lambda: webbrowser.open_new_tab(f"http://{HOST}:{port}{paths[where]}")).start()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--open", default="home", choices=["home", "split", "teacher", "student", "none"])
    a = ap.parse_args()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lesson = json.loads(LESSON_FILE.read_text(encoding="utf-8"))
    Handler.engine, Handler.token = Engine(lesson), token()
    try:
        srv = Server((HOST, a.port), Handler)
    except OSError:
        try:
            r = json.load(urllib.request.urlopen(f"http://{HOST}:{a.port}/api/health", timeout=2))
            if r.get("app") == "roots-sync":
                print(f"ROOTS is already running on port {a.port}. Opening it in your browser.")
                open_browser(a.port, a.open); time.sleep(1.5); return
        except Exception:
            pass
        sys.exit(f"Port {a.port} is used by another program. Close it, or run:  python server.py --port 8780")
    print("=" * 62)
    print("  ROOTS M0.2 is running (offline, this laptop only)")
    print(f"  Launcher        http://{HOST}:{a.port}/")
    print(f"  Teacher         http://{HOST}:{a.port}/teacher")
    print(f"  Student display http://{HOST}:{a.port}/student")
    print(f"  Side by side    http://{HOST}:{a.port}/split")
    print("  KEEP THIS WINDOW OPEN. Close it (or press Ctrl+C) to stop ROOTS.")
    print("=" * 62)
    open_browser(a.port, a.open)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
