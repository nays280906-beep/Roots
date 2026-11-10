/* ROOTS visuals: mascot "Beeju", fraction illustrations, learning path, tree. Pure SVG strings, no network. */
(function () {
  const INK = "#2F3E46";
  const P = { // [pastel fill, deeper accent, text-dark]
    mint: ["#BDEBD2", "#5CC596", "#2A7F5A"], sky: ["#BFE3F7", "#5BB4E6", "#25709F"],
    yellow: ["#FFE79A", "#F2C94C", "#9A7A12"], peach: ["#FFD3BA", "#F4A582", "#B85A2E"],
    lavender: ["#DCCBF5", "#A98AE3", "#6444AC"]
  };
  const L = {
    numerator: { en: "numerator", hi: "अंश" }, denominator: { en: "denominator", hi: "हर" },
    equal: { en: "Equal parts", hi: "बराबर हिस्से" }, unequal: { en: "Not equal", hi: "बराबर नहीं" },
    greater: { en: "is greater than", hi: "बड़ा है" }
  };
  const lbl = (k, lang) => (L[k][lang] || L[k].en);
  const svg = (vb, inner, cls = "") => `<svg class="vis ${cls}" viewBox="${vb}" xmlns="http://www.w3.org/2000/svg" role="img" aria-hidden="true">${inner}</svg>`;

  function slice(cx, cy, r, a0, a1) {
    const x0 = cx + r * Math.sin(a0), y0 = cy - r * Math.cos(a0), x1 = cx + r * Math.sin(a1), y1 = cy - r * Math.cos(a1);
    return `M${cx} ${cy}L${x0.toFixed(2)} ${y0.toFixed(2)}A${r} ${r} 0 ${(a1 - a0) > Math.PI ? 1 : 0} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}Z`;
  }
  function pieInner(cx, cy, r, num, den, fill, ring = "#7C8E97") {
    let s = "";
    if (den === 1) s += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${num ? fill : "#FFFDF5"}"/>`;
    else for (let i = 0; i < den; i++) {
      s += `<path d="${slice(cx, cy, r, 2 * Math.PI * i / den, 2 * Math.PI * (i + 1) / den)}" fill="${i < num ? fill : "#FFFDF5"}" stroke="${ring}" stroke-width="3.5" stroke-linejoin="round"/>`;
    }
    return s + `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${ring}" stroke-width="6"/>`;
  }

  function pie(v) {
    const c = P[v.color || "peach"];
    return svg("0 0 260 260", pieInner(130, 130, 108, v.num, v.den, c[1], c[2]), "v-pie");
  }
  function bar(v) {
    const c = P[v.color || "mint"], n = v.den, w = 600, x0 = 20, y = 55, h = 92, sw = w / n;
    let s = `<defs><clipPath id="bc${n}${v.num}"><rect x="${x0}" y="${y}" width="${w}" height="${h}" rx="26"/></clipPath></defs><g clip-path="url(#bc${n}${v.num})">`;
    for (let i = 0; i < n; i++) s += `<rect x="${x0 + i * sw}" y="${y}" width="${sw}" height="${h}" fill="${i < v.num ? c[1] : "#FFFDF5"}"/>`;
    for (let i = 1; i < n; i++) s += `<line x1="${x0 + i * sw}" y1="${y}" x2="${x0 + i * sw}" y2="${y + h}" stroke="${c[2]}" stroke-width="4"/>`;
    s += `</g><rect x="${x0}" y="${y}" width="${w}" height="${h}" rx="26" fill="none" stroke="${c[2]}" stroke-width="6"/>`;
    return svg("0 0 640 200", s, "v-bar");
  }
  function pieLabel(v, lang) {
    const pc = P.peach, sc = P.sky;
    let s = pieInner(130, 140, 108, v.num, v.den, pc[1], sc[1]);
    s += `<text x="400" y="128" text-anchor="middle" font-size="104" font-weight="900" fill="${pc[2]}">${v.num}</text>`;
    s += `<line x1="335" y1="152" x2="465" y2="152" stroke="${INK}" stroke-width="8" stroke-linecap="round"/>`;
    s += `<text x="400" y="244" text-anchor="middle" font-size="104" font-weight="900" fill="${sc[2]}">${v.den}</text>`;
    s += `<text x="480" y="104" font-size="30" font-weight="800" fill="${pc[2]}">${lbl("numerator", lang)}</text>`;
    s += `<text x="480" y="220" font-size="30" font-weight="800" fill="${sc[2]}">${lbl("denominator", lang)}</text>`;
    return svg("0 0 700 280", s, "v-label");
  }
  function equalVsUnequal(v, lang) {
    const m = P.mint, l = P.lavender;
    let s = pieInner(170, 135, 100, 2, 4, m[1], m[2]).replace(/fill="#FFFDF5"/g, `fill="${m[0]}"`);
    // unequal circle: slices of 12, 100, 90, 158 degrees
    const cuts = [0, 12, 112, 202, 360].map(d => d * Math.PI / 180), cx = 470, cy = 135, r = 100;
    for (let i = 0; i < 4; i++) s += `<path d="${slice(cx, cy, r, cuts[i], cuts[i + 1])}" fill="${i % 2 ? l[0] : l[1]}" stroke="${l[2]}" stroke-width="3.5" stroke-linejoin="round"/>`;
    s += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${l[2]}" stroke-width="6"/>`;
    s += `<rect x="70" y="252" width="200" height="46" rx="23" fill="${m[0]}"/><path d="M92 276l8 8 15-17" fill="none" stroke="${m[2]}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><text x="196" y="285" text-anchor="middle" font-size="26" font-weight="800" fill="${m[2]}">${lbl("equal", lang)}</text>`;
    s += `<rect x="370" y="252" width="200" height="46" rx="23" fill="${l[0]}"/><text x="470" y="285" text-anchor="middle" font-size="26" font-weight="800" fill="${l[2]}">${lbl("unequal", lang)}</text>`;
    return svg("0 0 640 310", s, "v-equal");
  }
  function numberline(v) {
    const n = v.den, x0 = 50, x1 = 590, y = 150, c = P.peach, sc = P.sky, X = i => x0 + (x1 - x0) * i / n;
    let s = `<line x1="${x0}" y1="${y}" x2="${x1}" y2="${y}" stroke="${sc[1]}" stroke-width="10" stroke-linecap="round"/>`;
    for (let i = 0; i < v.mark; i++)
      s += `<path d="M${X(i)} ${y - 12} Q${(X(i) + X(i + 1)) / 2} ${y - 100} ${X(i + 1)} ${y - 14}" fill="none" stroke="${c[1]}" stroke-width="6" stroke-linecap="round" stroke-dasharray="1 12"/>`;
    for (let i = 0; i <= n; i++) {
      s += `<line x1="${X(i)}" y1="${y - 16}" x2="${X(i)}" y2="${y + 16}" stroke="${INK}" stroke-width="5" stroke-linecap="round"/>`;
      const t = i === 0 ? "0" : i === n ? "1" : `${i}/${n}`;
      s += `<text x="${X(i)}" y="${y + 52}" text-anchor="middle" font-size="${i === 0 || i === n ? 36 : 28}" font-weight="900" fill="${INK}">${t}</text>`;
    }
    s += `<circle cx="${X(v.mark)}" cy="${y}" r="19" fill="${c[1]}" stroke="#fff" stroke-width="6"/>`;
    s += `<text x="${X(v.mark)}" y="262" text-anchor="middle" font-size="52" font-weight="900" fill="${c[2]}">${v.mark}/${n}</text>`;
    return svg("0 0 640 290", s, "v-line");
  }
  function compareBars(v, lang) {
    const [a, b] = [v.a, v.b], big = a[0] / a[1] > b[0] / b[1] ? a : b, small = big === a ? b : a;
    const row = (f, y, c) => {
      const n = f[1], w = 420, x0 = 30, sw = w / n, id = `cb${y}`;
      let s = `<defs><clipPath id="${id}"><rect x="${x0}" y="${y}" width="${w}" height="64" rx="20"/></clipPath></defs><g clip-path="url(#${id})">`;
      for (let i = 0; i < n; i++) s += `<rect x="${x0 + i * sw}" y="${y}" width="${sw}" height="64" fill="${i < f[0] ? c[1] : "#FFFDF5"}"/>`;
      for (let i = 1; i < n; i++) s += `<line x1="${x0 + i * sw}" y1="${y}" x2="${x0 + i * sw}" y2="${y + 64}" stroke="${c[2]}" stroke-width="3.5"/>`;
      return s + `</g><rect x="${x0}" y="${y}" width="${w}" height="64" rx="20" fill="none" stroke="${c[2]}" stroke-width="5"/><text x="${x0 + w + 40}" y="${y + 48}" font-size="58" font-weight="900" fill="${c[2]}">${f[0]}/${f[1]}</text>`;
    };
    return svg("0 0 640 270", row(a, 20, P.sky) + row(b, 120, P.peach) +
      `<text x="320" y="240" text-anchor="middle" font-size="46" font-weight="900" fill="${INK}">${big[0]}/${big[1]}  &gt;  ${small[0]}/${small[1]}</text>`, "v-compare");
  }
  function visual(v, lang) {
    if (!v) return "";
    return ({ pie, bar, pie_label: pieLabel, equal_vs_unequal: equalVsUnequal, numberline, compare_bars: compareBars }[v.type] || (() => ""))(v, lang);
  }

  /* ---------------- Beeju, the seed-sprout mascot ---------------- */
  function beeju(mood = "happy") {
    const eyeOpen = `<ellipse cx="78" cy="140" rx="9" ry="12.5" fill="${INK}"/><ellipse cx="122" cy="140" rx="9" ry="12.5" fill="${INK}"/><circle cx="81" cy="135" r="3.8" fill="#fff"/><circle cx="125" cy="135" r="3.8" fill="#fff"/>`;
    const arc = (cx, d) => `<path d="M${cx - 12} ${142 + d} Q${cx} ${142 - 18 - d} ${cx + 12} ${142 + d}" fill="none" stroke="${INK}" stroke-width="6" stroke-linecap="round"/>`;
    const eyes = {
      happy: eyeOpen, encourage: eyeOpen,
      cheer: arc(78, 0) + arc(122, 0),
      think: `<ellipse cx="80" cy="136" rx="9" ry="12.5" fill="${INK}"/><ellipse cx="124" cy="136" rx="9" ry="12.5" fill="${INK}"/><circle cx="84" cy="130" r="3.8" fill="#fff"/><circle cx="128" cy="130" r="3.8" fill="#fff"/><path d="M108 116 q14 -9 28 -2" fill="none" stroke="${INK}" stroke-width="5" stroke-linecap="round"/>`,
      sleep: `<path d="M66 140 Q78 152 90 140" fill="none" stroke="${INK}" stroke-width="6" stroke-linecap="round"/><path d="M110 140 Q122 152 134 140" fill="none" stroke="${INK}" stroke-width="6" stroke-linecap="round"/>`
    }[mood] || eyeOpen;
    const smile = `<path d="M86 166 Q100 180 114 166" fill="none" stroke="${INK}" stroke-width="5.5" stroke-linecap="round"/>`;
    const mouth = {
      happy: smile, encourage: smile,
      cheer: `<path d="M80 160 Q100 196 120 160Z" fill="#7A3B3B" stroke="#7A3B3B" stroke-width="4" stroke-linejoin="round"/><path d="M90 177 Q100 168 110 177 Q100 186 90 177Z" fill="#FF8FA3"/>`,
      think: `<ellipse cx="106" cy="170" rx="6" ry="7.5" fill="#7A3B3B"/>`,
      sleep: `<path d="M92 168 Q100 174 108 168" fill="none" stroke="${INK}" stroke-width="5" stroke-linecap="round"/>`
    }[mood] || smile;
    const arm = (d) => `<path d="${d}" fill="none" stroke="#D2A56B" stroke-width="11" stroke-linecap="round"/>`;
    const arms = {
      cheer: arm("M32 146 Q8 126 12 96") + arm("M168 146 Q192 126 188 96"),
      think: arm("M32 156 Q12 166 14 184") + arm("M168 156 Q150 180 122 172"),
      sleep: arm("M32 156 Q12 166 14 184") + arm("M168 156 Q188 166 186 184")
    }[mood] || (arm("M32 156 Q12 166 14 184") + arm("M168 150 Q194 150 192 120"));
    const extra = mood === "sleep" ? `<text x="150" y="86" font-size="30" font-weight="900" fill="#8FA4AE">z</text><text x="168" y="60" font-size="22" font-weight="900" fill="#8FA4AE">z</text>`
      : mood === "encourage" ? `<path d="M158 74 c-6 -12 -22 -4 -14 8 l14 12 l14 -12 c8 -12 -8 -20 -14 -8z" fill="#FF9FB2" transform="scale(.8) translate(40 6)"/>` : "";
    return svg("0 0 200 232", `
      <ellipse cx="100" cy="222" rx="62" ry="8" fill="#000" opacity=".08"/>
      ${arms}
      <path d="M100 64 C152 66 178 114 178 154 C178 198 144 216 100 216 C56 216 22 198 22 154 C22 114 48 66 100 64Z" fill="#F9DDB6" stroke="#D2A56B" stroke-width="5"/>
      <ellipse cx="60" cy="112" rx="13" ry="22" fill="#fff" opacity=".4" transform="rotate(20 60 112)"/>
      <ellipse cx="72" cy="216" rx="20" ry="8" fill="#D2A56B"/><ellipse cx="128" cy="216" rx="20" ry="8" fill="#D2A56B"/>
      <circle cx="58" cy="162" r="10" fill="#FFB3A7" opacity=".7"/><circle cx="142" cy="162" r="10" fill="#FFB3A7" opacity=".7"/>
      ${eyes}${mouth}${extra}
      <g class="leaves"><path d="M100 66 Q98 46 100 32" fill="none" stroke="#4FB07E" stroke-width="7" stroke-linecap="round"/>
      <path d="M100 38 C70 14 38 28 46 54 C74 58 94 50 100 38Z" fill="#8FE0B4" stroke="#4FB07E" stroke-width="4" stroke-linejoin="round"/>
      <path d="M100 38 C132 6 170 22 158 52 C130 60 106 52 100 38Z" fill="#A8EAC5" stroke="#4FB07E" stroke-width="4" stroke-linejoin="round"/></g>`, "beeju mood-" + mood);
  }

  function tree(stage = 0) {
    const soil = `<ellipse cx="80" cy="188" rx="66" ry="12" fill="#E9C9A0"/>`;
    const leaf = (x, y, r, flip = 1) => `<path d="M${x} ${y} q${14 * flip} -22 ${34 * flip} -14 q${-4 * flip} 20 ${-34 * flip} 14z" fill="#8FE0B4" stroke="#4FB07E" stroke-width="3" stroke-linejoin="round" transform="rotate(${r} ${x} ${y})"/>`;
    let s = soil;
    if (stage === 0) s += `<ellipse cx="80" cy="178" rx="15" ry="9" fill="#C99A63"/><ellipse cx="76" cy="175" rx="5" ry="3" fill="#fff" opacity=".4"/>`;
    if (stage === 1) s += `<path d="M80 182 Q78 160 80 142" stroke="#4FB07E" stroke-width="7" fill="none" stroke-linecap="round"/>${leaf(80, 148, 0, 1)}${leaf(80, 150, 0, -1)}`;
    if (stage === 2) s += `<path d="M80 184 Q76 150 80 104" stroke="#9A7B4F" stroke-width="9" fill="none" stroke-linecap="round"/>${leaf(80, 116, 0, 1)}${leaf(80, 118, 0, -1)}${leaf(79, 142, 0, 1)}${leaf(79, 144, 0, -1)}${leaf(80, 106, -20, 1)}`;
    if (stage >= 3) s += `<path d="M66 186 Q76 150 72 112 L88 112 Q84 150 94 186Z" fill="#B88A55"/>
      <circle cx="80" cy="86" r="44" fill="#A8EAC5" stroke="#4FB07E" stroke-width="4"/><circle cx="48" cy="104" r="30" fill="#BDEBD2" stroke="#4FB07E" stroke-width="4"/><circle cx="112" cy="104" r="30" fill="#BDEBD2" stroke="#4FB07E" stroke-width="4"/>
      <circle cx="66" cy="78" r="7" fill="#FFB38F"/><circle cx="96" cy="94" r="7" fill="#FFB38F"/><circle cx="50" cy="108" r="6" fill="#FFB38F"/><circle cx="112" cy="106" r="6" fill="#FFE07A"/><circle cx="84" cy="62" r="6" fill="#FFE07A"/>`;
    return svg("0 0 160 200", s, "tree stage-" + stage);
  }

  function starPts(cx, cy, R, r) {
    let p = [];
    for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rad = i % 2 ? r : R; p.push((cx + rad * Math.cos(a)).toFixed(1) + "," + (cy + rad * Math.sin(a)).toFixed(1)); }
    return p.join(" ");
  }
  function starIcon(lit) {
    return svg("0 0 40 40", `<polygon points="${starPts(20, 21, 18, 8.5)}" fill="${lit ? "#FFD84D" : "#E9EFEA"}" stroke="${lit ? "#E5B422" : "#CFDAD3"}" stroke-width="2.5" stroke-linejoin="round"/>`, "star" + (lit ? " lit" : ""));
  }
  function shapeIcon(letter) {
    const f = { A: P.mint[2], B: P.sky[2], C: P.yellow[2], D: P.lavender[2] }[letter];
    const g = { A: `<circle cx="20" cy="20" r="14" fill="${f}"/>`, B: `<rect x="7" y="7" width="26" height="26" rx="5" fill="${f}"/>`,
      C: `<path d="M20 5 L36 33 L4 33Z" fill="${f}" stroke="${f}" stroke-width="3" stroke-linejoin="round"/>`, D: `<polygon points="${starPts(20, 21, 17, 8)}" fill="${f}" stroke="${f}" stroke-width="2" stroke-linejoin="round"/>` }[letter];
    return svg("0 0 40 40", g, "shape");
  }

  function pathSVG(path) {
    const n = path.length; if (!n) return "";
    const x0 = 44, x1 = 956, pts = path.map((p, i) => [x0 + (x1 - x0) * i / Math.max(n - 1, 1), 34 + 11 * Math.sin(i * 1.25)]);
    let segs = "";
    for (let i = 0; i < n - 1; i++) {
      const [ax, ay] = pts[i], [bx, by] = pts[i + 1], dx = (bx - ax) / 2, done = path[i].state === "done";
      segs += `<path d="M${ax} ${ay} C${ax + dx} ${ay} ${bx - dx} ${by} ${bx} ${by}" fill="none" stroke="${done ? "#5CC596" : "#D6E3DB"}" stroke-width="${done ? 9 : 7}" stroke-linecap="round"${done ? "" : ' stroke-dasharray="1 14"'}/>`;
    }
    let nodes = "";
    path.forEach((p, i) => {
      const [x, y] = pts[i], star = p.kind === "quiz";
      const fill = p.state === "done" ? "#5CC596" : p.state === "current" ? "#FFD84D" : "#EEF4F0";
      const stroke = p.state === "done" ? "#2A7F5A" : p.state === "current" ? "#E5B422" : "#CAD8D0";
      if (p.state === "current") nodes += `<circle class="ring" cx="${x}" cy="${y}" r="${star ? 26 : 23}" fill="none" stroke="#FFD84D" stroke-width="5" opacity=".7"/>`;
      nodes += star ? `<polygon points="${starPts(x, y + 1, 21, 10)}" fill="${fill}" stroke="${stroke}" stroke-width="4" stroke-linejoin="round"/>`
        : `<circle cx="${x}" cy="${y}" r="${p.state === "current" ? 17 : 14}" fill="${fill}" stroke="${stroke}" stroke-width="4"/>`;
      if (p.state === "done") nodes += `<path d="M${x - 6} ${y + 1} l5 6 l9 -11" fill="none" stroke="#fff" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>`;
    });
    return `<svg viewBox="0 0 1000 68" class="pathsvg" preserveAspectRatio="xMidYMid meet" aria-hidden="true">${segs}${nodes}</svg>`;
  }

  window.RV = { visual, beeju, tree, starIcon, shapeIcon, pathSVG, P };
})();
