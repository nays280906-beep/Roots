/* ROOTS teacher control: sends commands, renders the teacher view (includes private notes + answer key). */
(function () {
  const $ = (s) => document.querySelector(s), $$ = (s) => [...document.querySelectorAll(s)], E = RC.esc;
  const token = document.querySelector('meta[name="roots-token"]').content;
  let S = null, toastT;
  $("#logo").innerHTML = RV.beeju("happy");
  const PHASE = { idle: "Waiting to start", lesson: "Lesson in progress", quiz: "Quiz in progress", summary: "Lesson finished", ended: "Lesson ended" };

  function toast(msg) { const t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => t.hidden = true, 3200); }
  async function send(action, extra = {}) {
    try {
      const r = await fetch("/api/command", { method: "POST", headers: { "Content-Type": "application/json", "X-Roots-Token": token }, body: JSON.stringify({ action, ...extra }) });
      const j = await r.json(); if (!j.ok) toast(j.error || "That did not work.");
    } catch (e) { toast("Cannot reach the ROOTS server. Is its window still open?"); }
  }

  function render(s) {
    S = s; const c = s.can;
    $("#phase").textContent = PHASE[s.phase];
    $$("[data-act]").forEach(b => { b.disabled = !c[b.dataset.act]; });
    $('[data-act="reset"]').hidden = !c.reset;
    $("#nextLbl").textContent = s.phase === "quiz" && s.question && s.question.index === s.lesson.questions - 1 ? "Finish" : "Next";
    $$(".seg button").forEach(b => b.setAttribute("aria-pressed", b.dataset.lang === s.lang));
    const n = s.connections.public;
    const cs = $("#chipStudent"); cs.dataset.s = n ? "ok" : "warn";
    cs.lastElementChild.textContent = n ? `Student display: connected (${n} window${n > 1 ? "s" : ""})` : "Student display: not open";

    let now = "", notes = "", key = "";
    if (s.phase === "lesson") {
      const sl = s.slide;
      now = `<div class="sub">Slide ${sl.index + 1} of ${sl.total}</div><div class="big">${E(sl.title)}</div><ul style="margin:0;padding-left:20px">${sl.body.map(b => `<li>${E(b)}</li>`).join("")}</ul>`;
      if (s.notes) notes = `<div class="note"><b>Teacher note · students cannot see this</b>${E(s.notes)}</div>`;
    } else if (s.phase === "quiz") {
      const q = s.question;
      now = `<div class="sub">Question ${q.index + 1} of ${q.total} · hints shown: ${q.hints.length} of ${s.answer_key.hint_total} · answer ${q.revealed ? "revealed" : "hidden"}</div><div class="big">${E(q.prompt)}</div>
        <div class="opts">${q.options.map(o => `<div class="opt${o.letter === s.answer_key.letter ? " right" : ""}"><b>${o.letter}</b>${E(o.text)}</div>`).join("")}</div>`;
      key = `<div class="keybox"><b>Answer key · students cannot see this yet</b>Correct answer: ${s.answer_key.letter} (${E(s.answer_key.text)})</div>`;
    } else {
      const msg = { idle: ["Ready when you are.", "Press Start Lesson. The student screen will change instantly."], summary: ["Lesson finished.", "Press End Lesson, or Start Lesson to run it again."], ended: ["Lesson ended.", "Press Start Lesson to teach it again."] }[s.phase];
      now = `<div class="empty">${RV.beeju(s.phase === "idle" ? "sleep" : "happy")}<div class="big">${msg[0]}</div><div>${msg[1]}</div></div>`;
    }
    $("#now").innerHTML = now; $("#notes").innerHTML = notes; $("#key").innerHTML = key;
    $("#slides").innerHTML = s.phase === "lesson" ? `<div class="sub" style="margin-top:6px">Jump to slide</div><div class="slist">${s.slide_titles.map((t, i) =>
      `<button type="button" data-goto="${i}" title="${E(t)}" ${i === s.slide.index ? 'aria-current="true"' : ""}>${i + 1}</button>`).join("")}</div>` : "";
    $$("[data-goto]").forEach(b => b.onclick = () => send("goto", { index: +b.dataset.goto }));
  }

  $$("[data-act]").forEach(b => b.addEventListener("click", () => send(b.dataset.act)));
  $$(".seg button").forEach(b => b.addEventListener("click", () => send("set_language", { lang: b.dataset.lang })));
  $("#openWin").onclick = () => window.open("/student", "roots_student", "popup=yes,width=1100,height=640");
  $("#openFs").onclick = () => window.open("/student?fs=1", "roots_student", "popup=yes,width=1100,height=640");
  $("#openSplit").onclick = () => { location.href = "/split"; };
  addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey || /input|textarea|select/i.test(e.target.tagName)) return;
    const k = e.key.toLowerCase(), c = S && S.can; if (!c) return;
    if (k === "arrowright") { e.preventDefault(); send("next"); }
    else if (k === "arrowleft") { e.preventDefault(); send("prev"); }
    else if (k === " ") { e.preventDefault(); send(c.reveal ? "reveal" : "next"); }
    else if (k === "r") send("reveal"); else if (k === "h") send("hint"); else if (k === "q") send("start_quiz");
  });
  RC.connect({ channel: "teacher", token, onState: render,
    onStatus: (st) => { const c = $("#chipServer"); c.dataset.s = st === "live" ? "ok" : "warn"; c.lastElementChild.textContent = st === "live" ? "Server connected" : "Reconnecting to server…"; } });
})();
