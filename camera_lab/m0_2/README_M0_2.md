# ROOTS M0.2 — Teacher + Student display on ONE laptop

Two browser windows, one small local server, live sync, no internet, **no `pip install`**.

```
 Teacher window  --(button click)-->  server.py  --(instant push)-->  Student display window
   /teacher           POST /api/command   127.0.0.1:8765     SSE        /student
```
The server holds the one true lesson state. The student display can only *receive*; it has no
buttons and no token. It never receives the answer key (until you press Reveal), teacher notes,
or any student record.

## 1. One-time setup (Windows 10/11)
1. Install **Python 3.10 or newer** from python.org (needs internet once). In the installer, **tick "Add python.exe to PATH"**.
2. Unzip this folder anywhere, e.g. `C:\ROOTS\roots_m0_2`.
3. That's it. No packages to install. Fonts and icons are bundled. Everything runs offline.

## 2. Launch
| Double-click | What happens |
|---|---|
| **`Start_SideBySide.bat`** | Opens teacher + student side by side in one browser window (your test mode) |
| **`Start_ROOTS.bat`** | Opens a menu page: teacher, student window, student full-screen, side-by-side |
| **`Start_Student_Fullscreen.bat`** | Starts the server and opens only the student display, full screen (for the projector) |

A black server window opens. **Keep it open** while teaching; closing it stops ROOTS.
Windows may show a firewall prompt the first time. ROOTS only listens on `127.0.0.1` (this laptop), so you can click *Cancel*.

## 3. Try it (5 minutes, laptop only)
1. Run `Start_SideBySide.bat`. Left = teacher, right = student display (a 16:9 "projector preview").
2. Press **Start Lesson**. The right side changes instantly. Use **Next / Previous** (or the arrow keys).
3. Press **Start Quiz**, **Show Hint** (shown in Beeju's speech bubble), then **Reveal Answer**: confetti, the correct tile lights up, the explanation appears.
4. Click **हिन्दी** to switch the student display to Hindi mid-lesson.
5. Finish the 5 questions → celebration screen → **End Lesson**.

### Two real windows (instead of side-by-side)
Run `Start_ROOTS.bat`, open **Teacher window**, then press **Open student window**. Put them next to each other (Win+← / Win+→).

### Full screen on this one screen
Press **Open full-screen display** (or run `Start_Student_Fullscreen.bat`). The student display fills the screen. Use **Alt+Tab** to return to the teacher window; the display keeps updating behind it. Press **F** (or Esc) on the student display to leave full screen.

### When you later get a projector
Open the student window, **drag it onto the projector screen**, press **F11** or its *Full screen* button. Nothing else changes. Windows: set the projector to *Extend* (Win+P).

## 4. Teacher controls
Start Lesson · Previous · Next · Start Quiz · Show Hint · Reveal Answer · End Lesson · language toggle · jump-to-slide.
Buttons grey out when they don't apply (e.g. Reveal before a quiz). Keys: **← →** navigate, **Space** next/reveal, **H** hint, **R** reveal, **Q** quiz.
The state is saved in `data\live_state.json`, so closing and reopening ROOTS resumes where you were.

## 5. What was verified, and what was NOT

**Verified (automated, in a Linux sandbox with real Chromium; 40 server checks + 25 browser checks):**
- Two separate pages sync: every teacher control (all 6 required, plus hint, jump, language) updates the student page; median click→screen ≈ 65 ms.
- Server rules: refuses invalid moves (e.g. Next before Reveal), bad token, foreign Host, path traversal.
- Privacy: answer key absent from the student channel until Reveal; no teacher fields leak.
- Persistence across server restart; both pages auto-reconnect after a server restart.
- No external network requests; bundled Nunito + Devanagari fonts load; no console errors.
- No page overflow at 1920×1080, 1100×620, 800×1000; auto-fit text.

**NOT verified (needs your laptop):**
- The four `.bat` launchers and the Edge/Chrome full-screen flags (written carefully, never run on Windows).
- A real projector, real extended display, real classroom distance/readability.
- Behaviour on your specific browser version. Tested only on Chromium. Edge and Chrome should match; Firefox untested.
- **The Hindi text is a draft** and must be reviewed by a native Hindi-speaking teacher before classroom use.

## 6. Troubleshooting
| Problem | Fix |
|---|---|
| "Python 3 was not found" | Install from python.org and tick *Add python.exe to PATH*. Opening a Microsoft Store page instead means the Store stub was hit: install the real Python. |
| "Port 8765 is used by another program" | Close other ROOTS windows. Or: `py -3 server.py --port 8780` and use that port in the URLs. |
| "Open student window" does nothing | Your browser blocked the pop-up: allow pop-ups for `127.0.0.1`, or use the Menu page's **Student display** card. |
| Student screen says "Reconnecting…" | The black server window was closed. Start ROOTS again; pages reconnect by themselves. |
| Teacher says "token missing or old" | Reload the teacher page (F5). |
| Full screen won't start from the pop-up | Browsers need one click on the student page. Click anywhere, or press **F**. |
| Hindi looks wrong | Reload the student page once; fonts are in `web\fonts`. |

## 7. For developers
- `python tests\test_sync.py` — server tests (stdlib only, no browser).
- `python tests\browser_check.py` — real two-page browser test (dev-only; needs `playwright` and a Chromium binary in `CHROMIUM_PATH`).
- Lesson content: `data\lessons\fractions_c5.json` (EN/HI per string). Student pages render only what `Engine.view("public")` returns in `server.py`.

## 8. Architecture finding for the main ROOTS build (needs your decision)
The student display is **plain HTML/JS served by a small local server**, not Streamlit. Streamlit re-runs scripts and would flicker and add latency on a projector, and cannot give this instant push. The teacher side can later either stay as this page or become a Streamlit app that calls the same `/api/command` endpoint; SQLite replaces `live_state.json` behind the same interface.
