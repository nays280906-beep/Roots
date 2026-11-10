"""Dev-only: drives two real browser pages (teacher + student) against a live server. Needs playwright + a Chromium binary (CHROMIUM_PATH)."""
import os, subprocess, sys, tempfile, time, socket, json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(os.environ.get("SHOTS", "/tmp/shots")); OUT.mkdir(exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
st = tempfile.mkdtemp()
srv = subprocess.Popen([sys.executable, str(ROOT / "server.py"), "--port", str(port), "--open", "none"], env=dict(os.environ, ROOTS_STATE_DIR=st), stdout=subprocess.DEVNULL)
time.sleep(1.0)
B = f"http://127.0.0.1:{port}"
res = []
def check(n, c, d=""): res.append(c); print(("PASS  " if c else "FAIL  ") + n + (f"  [{d}]" if d else ""))
ARGS = ["--no-sandbox", "--disable-gpu", "--disable-software-rasterizer", "--in-process-gpu", "--disable-dev-shm-usage"]
try:
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=os.environ["CHROMIUM_PATH"], args=ARGS)
        ctx = br.new_context(viewport={"width": 1366, "height": 768})
        external, errors = [], []
        ctx.on("request", lambda r: external.append(r.url) if not r.url.startswith((B, "data:", "blob:")) else None)
        tp, sp = ctx.new_page(), ctx.new_page()      # two separate pages = two windows
        for pg in (tp, sp):
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errors.append(str(e)))
        sp.set_viewport_size({"width": 1280, "height": 720})
        tp.goto(B + "/teacher"); sp.goto(B + "/student")
        tp.wait_for_selector("#phase:not(:empty)")
        tp.wait_for_function("document.querySelector('#chipStudent').dataset.s==='ok'", timeout=4000)
        check("teacher sees the student window connect", True)
        check("full-screen prompt overlay is NOT visible on a normal launch", sp.evaluate("(()=>{const e=document.getElementById('fsprompt');return getComputedStyle(e).display==='none'})()"))
        check("student shows waiting screen", "Waiting" in sp.inner_text("#stage"))
        check("controls disabled correctly at start", tp.is_disabled('[data-act=next]') and tp.is_disabled('[data-act=reveal]') and tp.is_enabled('[data-act=start_lesson]'))
        sp.screenshot(path=str(OUT / "01_student_idle.png")); tp.screenshot(path=str(OUT / "01_teacher_idle.png"))

        def click_and_time(sel, pred_js):
            t0 = time.perf_counter(); tp.click(sel); sp.wait_for_function(pred_js, timeout=3000); return (time.perf_counter() - t0) * 1000
        lat = []
        lat.append(click_and_time("[data-act=start_lesson]", "document.querySelector('.view.lesson')"))
        check("Start Lesson updates student page", "fractions" in sp.inner_text("#stage").lower())
        sp.wait_for_timeout(700); sp.screenshot(path=str(OUT / "02_student_slide1.png"))
        lat.append(click_and_time("[data-act=next]", "document.querySelector('.chip') && document.querySelector('.chip').textContent.includes('2 of')"))
        check("Next Slide updates student page", "denominator" in sp.inner_text("#stage").lower())
        sp.wait_for_timeout(700); sp.screenshot(path=str(OUT / "03_student_slide2.png"))
        lat.append(click_and_time("[data-act=prev]", "document.querySelector('.chip').textContent.includes('1 of')"))
        check("Previous Slide updates student page", True)
        for i in range(5): tp.click("[data-act=next]"); sp.wait_for_timeout(120)
        sp.wait_for_timeout(600); sp.screenshot(path=str(OUT / "04_student_slide6.png"))
        tp.keyboard.press("Home")
        lat.append(click_and_time("[data-act=start_quiz]", "document.querySelector('.view.quiz')"))
        check("Start Quiz updates student page", sp.locator(".tile").count() == 4)
        tp.wait_for_selector(".keybox"); check("teacher sees answer key", "B" in tp.inner_text("#key"))
        check("student page does NOT contain the answer before reveal", sp.locator(".tile.correct").count() == 0 and "answer is" not in sp.inner_text("#rail").lower())
        sp.wait_for_timeout(700); sp.screenshot(path=str(OUT / "05_student_quiz.png")); tp.screenshot(path=str(OUT / "05_teacher_quiz.png"))
        lat.append(click_and_time("[data-act=hint]", "document.querySelector('.bubble.hint')"))
        check("Show Hint appears in speech bubble", "Hint 1" in sp.inner_text("#rail"))
        sp.wait_for_timeout(600); sp.screenshot(path=str(OUT / "06_student_hint.png"))
        lat.append(click_and_time("[data-act=reveal]", "document.querySelector('.tile.correct')"))
        check("Reveal Answer highlights tile B and explains", sp.locator(".tile.correct").inner_text().strip().endswith("1/4") and "The answer is" in sp.inner_text("#rail"))
        sp.wait_for_timeout(500); sp.screenshot(path=str(OUT / "07_student_reveal_confetti.png"))
        sp.wait_for_timeout(2600); sp.screenshot(path=str(OUT / "08_student_reveal_after.png"))
        # Hindi
        lat.append(click_and_time("[data-lang=hi]", "document.documentElement.lang==='hi'"))
        check("Language switch to Hindi reaches student", "रोटी" in sp.inner_text("#stage"))
        sp.wait_for_timeout(600); sp.screenshot(path=str(OUT / "09_student_hindi_reveal.png"))
        tp.screenshot(path=str(OUT / "09_teacher_hindi.png"))
        for i in range(4): tp.click("[data-act=next]"); sp.wait_for_timeout(150); tp.click("[data-act=reveal]"); sp.wait_for_timeout(150)
        tp.click("[data-act=next]"); sp.wait_for_function("document.querySelector('h1') && document.querySelector('h1').textContent.includes('कर दिखाया')", timeout=3000)
        check("summary screen reaches student", True)
        sp.wait_for_timeout(800); sp.screenshot(path=str(OUT / "10_student_summary_hi.png"))
        tp.click("[data-lang=en]"); sp.wait_for_timeout(300)
        lat.append(click_and_time("[data-act=end_lesson]", "document.querySelector('h1') && document.querySelector('h1').textContent.includes('See you')"))
        check("End Lesson updates student page", True); sp.screenshot(path=str(OUT / "11_student_ended.png"))
        # refusal toast
        tp.click("[data-act=start_lesson]"); sp.wait_for_selector(".view.lesson"); tp.keyboard.press("ArrowLeft")
        tp.wait_for_selector("#toast:not([hidden])", timeout=2000); check("refused action shows friendly message", "first slide" in tp.inner_text("#toast"))
        lat.sort(); print(f"      click -> student DOM updated: median {lat[len(lat)//2]:.0f} ms, max {lat[-1]:.0f} ms ({len(lat)} actions)")
        check("click-to-screen median < 300 ms", lat[len(lat)//2] < 300)
        # reconnect: restart server, pages recover
        srv.terminate(); srv.wait(); time.sleep(1.0)
        srv = subprocess.Popen([sys.executable, str(ROOT / "server.py"), "--port", str(port), "--open", "none"], env=dict(os.environ, ROOTS_STATE_DIR=st), stdout=subprocess.DEVNULL)
        sp.wait_for_function("document.querySelector('#conn').hidden===true", timeout=9000)
        tp.wait_for_function("document.querySelector('#chipServer').dataset.s==='ok'", timeout=9000)
        tp.click("[data-act=next]"); sp.wait_for_function("document.querySelector('.chip').textContent.includes('2 of')", timeout=3000)
        check("both pages auto-reconnect after a server restart and sync again", True)
        # layouts
        for name, w, h in [("1920x1080 projector", 1920, 1080), ("portrait tablet-ish 800x1000", 800, 1000), ("small laptop 1100x620", 1100, 620)]:
            sp.set_viewport_size({"width": w, "height": h}); sp.wait_for_timeout(400)
            sp.screenshot(path=str(OUT / f"12_layout_{w}x{h}.png"))
            ov = sp.evaluate("[document.documentElement.scrollHeight>innerHeight+2, document.documentElement.scrollWidth>innerWidth+2]")
            check(f"no page overflow at {name}", not any(ov), str(ov))
        # split page
        sp2 = ctx.new_page(); sp2.set_viewport_size({"width": 1366, "height": 768}); sp2.goto(B + "/split"); sp2.wait_for_timeout(1500)
        sp2.screenshot(path=str(OUT / "13_split.png"))
        f = sp2.frame_locator("#ft"); g = sp2.frame_locator("#fs")
        f.locator("[data-act=next]").click(); sp2.wait_for_timeout(500)
        check("split mode: teacher iframe controls student iframe", "3 of" in g.locator(".chip").first.inner_text())
        sp2.screenshot(path=str(OUT / "13_split_after.png"))
        check("no external network requests (offline-safe)", not external, str(external[:3]))
        # the 409 is the deliberate "refused action" test and CONNECTION_REFUSED is the deliberate server restart
        real = [e for e in errors if "409" not in e and "ERR_CONNECTION_REFUSED" not in e]
        check("no unexpected JavaScript/console errors", not real, str(real[:3]))
        fl = sp.evaluate("[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family)")
        check("bundled Nunito AND Devanagari fonts loaded from local files", "Nunito" in fl and "Noto Sans Devanagari" in fl, str(fl))
        br.close()
finally:
    srv.terminate()
print(f"\n{sum(res)} passed, {len(res)-sum(res)} failed"); sys.exit(0 if all(res) else 1)
