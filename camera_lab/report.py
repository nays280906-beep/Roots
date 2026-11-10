"""
Turn results/trials.csv into FEASIBILITY_RESULTS.md.
Only reports what was actually recorded. Untested cells say NOT TESTED.

    python report.py --class-size 30 --target-distance 5 --target-size 15
"""
import argparse, csv, math
from collections import defaultdict
from pathlib import Path

ID_MIN, DECODE_MIN = 0.95, 0.90
HERE = Path(__file__).parent


def load():
    p = HERE / "results" / "trials.csv"
    if not p.exists():
        return []
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    for r in rows:
        for k in ("distance_m", "id_rate", "correct_rate", "mean_ms"):
            r[k] = float(r[k])
        for k in ("marker_cm", "n_cards_expected", "confident_wrong", "false_ids", "flagged_for_review"):
            r[k] = int(float(r[k]))
    return rows


def agg(rows):
    n = len(rows)
    return dict(n=n, idr=sum(r["id_rate"] for r in rows) / n, cor=sum(r["correct_rate"] for r in rows) / n,
                cw=sum(r["confident_wrong"] for r in rows), fp=sum(r["false_ids"] for r in rows),
                ms=sum(r["mean_ms"] for r in rows) / n)


def verdict(a):
    ok = a["idr"] >= ID_MIN and a["cor"] >= DECODE_MIN and a["cw"] == 0
    return "PASS" if ok else "FAIL"


def table(title, rows, keyfn, keyname):
    g = defaultdict(list)
    for r in rows:
        g[keyfn(r)].append(r)
    out = [f"\n### {title}\n", f"| {keyname} | trials | ID rate | correct rate | confident-but-wrong | false IDs | ms/frame | verdict |",
           "|---|---|---|---|---|---|---|---|"]
    for k in sorted(g, key=lambda x: (str(type(x)), x)):
        a = agg(g[k])
        out.append(f"| {k} | {a['n']} | {a['idr']*100:.0f}% | {a['cor']*100:.0f}% | {a['cw']} | {a['fp']} | {a['ms']:.0f} | **{verdict(a)}** |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--class-size", type=int, default=30)
    ap.add_argument("--target-distance", type=float, default=5)
    ap.add_argument("--target-size", type=int, default=15)
    a = ap.parse_args()
    rows = load()
    L = ["# ROOTS M0 - Camera Feasibility Results (REAL HARDWARE)\n",
         f"Pass rule per condition: mean ID rate >= {ID_MIN*100:.0f}%, mean correct-answer rate >= {DECODE_MIN*100:.0f}%, "
         "and ZERO confident-but-wrong results (a wrong answer the system would not have sent for teacher review).",
         "Computed only from results/trials.csv. Anything not recorded is shown as NOT TESTED.\n"]
    if not rows:
        L.append("**No trials recorded yet.** Run `python camera_lab.py` and press SPACE for each condition.")
        (HERE / "FEASIBILITY_RESULTS.md").write_text("\n".join(L), encoding="utf-8"); print("\n".join(L)); return
    L.append(f"Trials recorded: **{len(rows)}** | cameras/resolutions seen: {sorted({r['actual_wh'] for r in rows})}\n")
    L.append(table("By distance", rows, lambda r: r["distance_m"], "distance (m)"))
    L.append(table("By marker size", rows, lambda r: r["marker_cm"], "marker (cm)"))
    L.append(table("By lighting", rows, lambda r: r["lighting"], "lighting"))
    L.append(table("By resolution", rows, lambda r: r["actual_wh"], "resolution"))
    L.append(table("By number of cards in frame", rows, lambda r: r["n_cards_expected"], "cards"))
    tgt = [r for r in rows if abs(r["distance_m"] - a.target_distance) < 0.6 and r["marker_cm"] == a.target_size]
    L.append(f"\n## Decision at target ({a.target_distance} m, {a.target_size} cm marker, class of {a.class_size})\n")
    if not tgt:
        L.append("**NOT TESTED at the target distance and marker size.** No scan-mode decision can be made yet.")
    else:
        bylight = defaultdict(list)
        for r in tgt:
            bylight[r["lighting"]].append(r)
        worst = [l for l, rs in bylight.items() if verdict(agg(rs)) == "FAIL"]
        by_n = defaultdict(list)
        for r in tgt:
            by_n[r["n_cards_expected"]].append(r)
        passing = [n for n, rs in by_n.items() if verdict(agg(rs)) == "PASS"]
        max_ok = max(passing) if passing else 0
        L.append(f"- Lighting conditions tested at target: {sorted(bylight)}; failing: {sorted(worst) or 'none'}")
        L.append(f"- Largest card count that passed at target: **{max_ok}** (from {len(tgt)} trials; larger counts only count if tested)")
        if max_ok >= a.class_size and not worst:
            L.append(f"- **Full-class scan looks viable** for {a.class_size} cards in the conditions tested. Repeat in the real classroom, with real children, before relying on it.")
        elif max_ok >= 1:
            g = max(max_ok, 1)
            L.append(f"- **Use group-wise scanning**: groups of about {g} -> {math.ceil(a.class_size / g)} scans per question. Manual entry stays available.")
        else:
            L.append("- **No passing configuration at the target.** Options: bigger markers (A3), move camera closer/raise it, wider-seating rows scanned separately, 1080p camera, or manual entry only.")
        if any(r["confident_wrong"] for r in tgt):
            L.append("- WARNING: confident-but-wrong results occurred. Lower the 'confident' bar in aruco_core.py (ANGLE_OK_DEG / MIN_AGREE) before M5.")
    out = "\n".join(L)
    (HERE / "FEASIBILITY_RESULTS.md").write_text(out, encoding="utf-8"); print(out)


if __name__ == "__main__":
    main()
