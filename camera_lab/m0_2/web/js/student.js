/* ROOTS student display: renders whatever the server's PUBLIC state says. It holds no secrets and sends no commands. */
(function () {
  const $ = (s) => document.querySelector(s);
  const E = RC.esc;
  const STR = {
    en: { waiting: "Waiting for the lesson to start…", hello: "Hello, friends!", q: (i, n) => `Question ${i} of ${n}`, idea: (i, n) => `Idea ${i} of ${n}`,
      hint: "Hint", ans: "The answer is", cheers: ["Great thinking!", "Wonderful!", "Super work!", "Fantastic!"], think: "Take your time. Think it through!",
      done: "We did it!", doneLine: (s, q) => `We explored ${s} ideas and answered ${q} questions together.`, bye: "See you next time!", byeSub: "The lesson has ended.",
      fs: "Full screen", fsExit: "Exit full screen", fsPrompt: "Click anywhere to start the full-screen lesson", reconnect: "Reconnecting…" },
    hi: { waiting: "पाठ शुरू होने की प्रतीक्षा…", hello: "नमस्ते दोस्तो!", q: (i, n) => `प्रश्न ${i} / ${n}`, idea: (i, n) => `विचार ${i} / ${n}`,
      hint: "संकेत", ans: "उत्तर है", cheers: ["बहुत बढ़िया!", "शाबाश!", "वाह!", "शानदार!"], think: "आराम से सोचिए!",
      done: "हमने कर दिखाया!", doneLine: (s, q) => `हमने ${s} बातें सीखीं और ${q} प्रश्न साथ मिलकर हल किए।`, bye: "फिर मिलेंगे!", byeSub: "पाठ समाप्त हुआ।",
      fs: "पूर्ण स्क्रीन", fsExit: "पूर्ण स्क्रीन बंद करें", fsPrompt: "पूर्ण स्क्रीन में पाठ शुरू करने के लिए कहीं भी क्लिक करें", reconnect: "फिर से जुड़ रहे हैं…" }
  };
  let S = null, lastKey = "", lastBurst = "", lastQ = -1;
  const T = (k, ...a) => { const v = STR[(S && S.lang) || "en"][k]; return typeof v === "function" ? v(...a) : v; };

  function stars(n, litCount) { let h = ""; for (let i = 0; i < n; i++) h += RV.starIcon(i < litCount); return `<div class="stars">${h}</div>`; }

  function viewLesson(s) {
    const sl = s.slide;
    return { mood: sl.mood, bubble: "", html: `<section class="view lesson enter">
      <article class="card text a${sl.accent}"><span class="chip">${E(T("idea", sl.index + 1, sl.total))}</span><h1>${E(sl.title)}</h1>
        <ul>${sl.body.map(b => `<li>${E(b)}</li>`).join("")}</ul></article>
      <article class="card visual-card">${RV.visual(sl.visual, s.lang)}</article></section>` };
  }

  function viewQuiz(s) {
    const q = s.question, tick = `<svg class="tick" viewBox="0 0 40 40"><circle cx="20" cy="20" r="19" fill="#5CC596"/><path d="M11 21l6 6 12-14" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    const lit = q.index + (q.revealed ? 1 : 0), hasVis = !!q.visual, still = q.index === lastQ; lastQ = q.index;
    const tiles = q.options.map(o => {
      const st = q.revealed ? (o.letter === q.correct ? " correct" : " dim") : "";
      return `<div class="tile ${o.letter}${st}"><div class="badge">${RV.shapeIcon(o.letter)}<b>${o.letter}</b></div><span class="label">${E(o.text)}</span>${tick}</div>`;
    }).join("");
    let bubble = "", mood = "think";
    if (q.revealed) {
      mood = "cheer";
      const c = T("cheers")[q.index % 4];
      bubble = `<div class="bubble good"><span class="hl"><span class="tag">${E(c)}</span>${E(T("ans"))} <b>${q.correct}</b></span>${E(q.explanation)}</div>`;
    } else if (q.hints.length) {
      const last = q.hints.length - 1;
      bubble = `<div class="bubble hint"><span class="tag">${E(T("hint"))} ${last + 1}</span>${E(q.hints[last])}</div>`;
    } else bubble = `<div class="bubble">${E(T("think"))}</div>`;
    return { mood, bubble, burst: q.revealed ? `${q.index}` : "", html: `<section class="view quiz${still ? " still" : ""}">
      <div class="qtop"><span class="chip">${E(T("q", q.index + 1, q.total))}</span>${stars(q.total, lit)}</div>
      <article class="card qcard${hasVis ? " hasvis" : ""}"><h1>${E(q.prompt)}</h1>${hasVis ? `<div class="qvis">${RV.visual(q.visual, s.lang)}</div>` : ""}</article>
      <div class="answers">${tiles}</div></section>` };
  }

  function render(s) {
    S = s;
    document.documentElement.lang = s.lang === "hi" ? "hi" : "en";
    document.body.dataset.lang = s.lang;
    const key = JSON.stringify([s.phase, s.lang, s.slide && s.slide.index, s.question && [s.question.index, s.question.revealed, s.question.hints.length], s.tree_stage]);
    if (key === lastKey) return;
    lastKey = key;
    if (s.phase !== "quiz") lastQ = -1;
    const path = $("#path"), rail = $("#rail");
    path.classList.toggle("hidden", !(s.phase === "lesson" || s.phase === "quiz" || s.phase === "summary"));
    path.innerHTML = RV.pathSVG(s.path || []);
    let v = null, center = "";
    if (s.phase === "lesson") v = viewLesson(s);
    else if (s.phase === "quiz") v = viewQuiz(s);
    else if (s.phase === "summary") center = `<section class="view center enter"><div class="hero">${RV.beeju("cheer")}${RV.tree(3)}</div>
      <h1>${E(T("done"))}</h1><p>${E(T("doneLine", s.summary.slides, s.summary.questions))}</p>${stars(s.summary.questions, s.summary.questions)}</section>`;
    else if (s.phase === "ended") center = `<section class="view center enter"><div class="hero">${RV.beeju("happy")}</div><h1>${E(T("bye"))}</h1><p>${E(T("byeSub"))}</p></section>`;
    else center = `<section class="view center enter"><div class="hero">${RV.beeju("sleep")}</div><h1>${E(T("hello"))}</h1><p>${E(T("waiting"))}</p>
      <span class="chip">${E(s.lesson.title)} · ${E(s.lesson.subtitle)}</span></section>`;
    $("#stage").innerHTML = v ? v.html : center;
    rail.classList.toggle("off", !v);
    rail.innerHTML = v ? `${RV.beeju(v.mood)}${v.bubble || '<div style="flex:1"></div>'}${RV.tree(s.tree_stage)}` : "";
    fit();
    if (v && v.burst && v.burst !== lastBurst) { lastBurst = v.burst; confetti(); }
    if (!v || !v.burst) lastBurst = "";
  }

  /* Shrink text until it fits its card (lessons differ in length; teachers will edit them). */
  function fit() {
    document.querySelectorAll(".lesson .text, .qcard, .bubble").forEach(el => {
      let f = 1; el.style.setProperty("--fs", 1);
      while ((el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1) && f > 0.5) { f -= 0.05; el.style.setProperty("--fs", f.toFixed(2)); }
    });
  }
  addEventListener("resize", () => { clearTimeout(fit.t); fit.t = setTimeout(fit, 80); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);

  /* ---------- confetti (no library) ---------- */
  function confetti() {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const c = $("#confetti"), x = c.getContext("2d"); c.width = innerWidth; c.height = innerHeight;
    const cols = ["#5CC596", "#5BB4E6", "#F2C94C", "#F4A582", "#A98AE3", "#FF8FA3"];
    const ps = Array.from({ length: 150 }, () => ({ x: innerWidth * (.15 + Math.random() * .7), y: innerHeight * .55, vx: (Math.random() - .5) * 16, vy: -(9 + Math.random() * 14),
      s: 6 + Math.random() * 9, r: Math.random() * 6, vr: (Math.random() - .5) * .4, c: cols[(Math.random() * 6) | 0], round: Math.random() < .35 }));
    const t0 = performance.now();
    (function frame(t) {
      const el = t - t0; x.clearRect(0, 0, c.width, c.height);
      ps.forEach(p => { p.vy += .42; p.x += p.vx; p.y += p.vy; p.vx *= .992; p.r += p.vr; x.save(); x.translate(p.x, p.y); x.rotate(p.r);
        x.globalAlpha = Math.max(0, 1 - el / 2600); x.fillStyle = p.c; p.round ? (x.beginPath(), x.arc(0, 0, p.s / 2, 0, 7), x.fill()) : x.fillRect(-p.s / 2, -p.s / 3, p.s, p.s * .66); x.restore(); });
      el < 2700 ? requestAnimationFrame(frame) : x.clearRect(0, 0, c.width, c.height);
    })(t0);
  }

  /* ---------- full screen ---------- */
  const fsb = $("#fsbtn"); let idleT;
  const isFS = () => !!document.fullscreenElement;
  function fsLabel() { fsb.textContent = isFS() ? T("fsExit") : T("fs"); }
  function toggleFS() { (isFS() ? document.exitFullscreen() : document.documentElement.requestFullscreen()).catch(() => {}); }
  fsb.addEventListener("click", toggleFS);
  addEventListener("keydown", (e) => { if (e.key === "f" || e.key === "F") toggleFS(); });
  document.addEventListener("fullscreenchange", fsLabel);
  function wake() { document.body.classList.remove("idle"); fsb.classList.remove("hide"); clearTimeout(idleT);
    idleT = setTimeout(() => { if (isFS()) { document.body.classList.add("idle"); fsb.classList.add("hide"); } }, 3000); }
  ["mousemove", "mousedown", "keydown", "touchstart"].forEach(ev => addEventListener(ev, wake)); wake();
  if (new URLSearchParams(location.search).get("fs") === "1") {
    const p = $("#fsprompt"); p.hidden = false;
    p.innerHTML = `${RV.beeju("cheer")}<h1 id="fsp"></h1>`;
    const setP = () => { $("#fsp").textContent = T("fsPrompt"); }; setP();
    p.addEventListener("click", () => { p.hidden = true; document.documentElement.requestFullscreen().catch(() => {}); });
  }

  /* ---------- go ---------- */
  fsLabel();
  RC.connect({ channel: "public",
    onState: (s) => { render(s); fsLabel(); },
    onStatus: (st) => { const c = $("#conn"); c.hidden = st === "live"; c.textContent = T("reconnect"); } });
})();
