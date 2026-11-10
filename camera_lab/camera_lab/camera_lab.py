"""
ROOTS M0 - Camera Lab. Run this on the teacher laptop with the REAL webcam.

    python camera_lab.py                       # live webcam (camera 0)
    python camera_lab.py --camera 1 --res 1920x1080
    python camera_lab.py --image photo.jpg     # test a phone photo instead of the webcam

Every trial is appended to results/trials.csv. Then run:  python report.py

Live keys:  SPACE = record a trial | E = edit conditions | S = save annotated snapshot
            Q / ESC = quit
Privacy: nothing is saved unless you press S. Do not save snapshots showing children.
"""
import argparse, csv, sys, time
from datetime import datetime
from pathlib import Path
import cv2
from aruco_core import Detector, detect_frame, aggregate, draw_overlay, LETTERS

RES_DIR = Path(__file__).parent / "results"
CSV_PATH = RES_DIR / "trials.csv"
FIELDS = ["timestamp", "distance_m", "marker_cm", "lighting", "resolution", "actual_wh", "n_cards_expected",
          "expected_spec", "params", "upscale", "frames", "ids_expected_found", "id_rate", "decoded_correct",
          "correct_rate", "false_ids", "flagged_for_review", "confident_wrong", "mean_ms", "notes"]
LIGHTING = ["bright_room", "normal_room", "dim_room", "window_backlight", "glare_on_card", "other"]


def parse_expected(spec: str) -> dict:
    """'0-4:A,5:B,6-9:C' -> {0:'A',...}. Each card is held at the stated answer."""
    out = {}
    for tok in spec.replace(" ", "").split(","):
        if not tok:
            continue
        ids, ans = tok.split(":")
        ans = ans.upper()
        if ans not in LETTERS:
            raise ValueError(f"answer must be A-D, got {ans}")
        a, b = (ids.split("-") + [ids])[:2] if "-" in ids else (ids, ids)
        for i in range(int(a), int(b) + 1):
            out[i] = ans
    return out


def ask(prompt, default=None, cast=str, choices=None):
    while True:
        s = input(f"{prompt}" + (f" [{default}]" if default not in (None, "") else "") + ": ").strip()
        if not s and default is not None:
            s = str(default)
        try:
            v = cast(s)
            if choices and v not in choices:
                print("  choose one of:", ", ".join(choices)); continue
            return v
        except Exception as e:
            print("  invalid:", e)


def setup(prev: dict) -> dict:
    print("\n--- Trial conditions (press Enter to keep the value in brackets) ---")
    s = dict(prev)
    s["distance_m"] = ask("Distance camera -> cards (metres, measured with a tape)", prev.get("distance_m", 3), float)
    s["marker_cm"] = ask("Marker size (black square side in cm: 10/15/20)", prev.get("marker_cm", 15), int)
    print("Lighting options:", ", ".join(f"{i+1}={n}" for i, n in enumerate(LIGHTING)))
    li = ask("Lighting number", LIGHTING.index(prev.get("lighting", "normal_room")) + 1, int)
    s["lighting"] = LIGHTING[li - 1]
    print("Who holds which card? e.g.  0-4:A   or   0:A,1:B,2:C,3:D   (every card must be held up)")
    s["expected_spec"] = ask("Expected", prev.get("expected_spec", "0:A"))
    s["notes"] = ask("Notes (angle, hands covering, anything odd; Enter for none)", "", str)
    return s


def get_frames(src, n):
    if src["kind"] == "image":
        return [src["img"]] * n
    cap, frames = src["cap"], []
    for _ in range(n):
        for _ in range(2):          # drop buffered frame so we get a fresh one
            cap.grab()
        ok, f = cap.read()
        if ok:
            frames.append(f)
        time.sleep(0.12)
    return frames


def record(src, det, cfg, args):
    exp = parse_expected(cfg["expected_spec"])
    frames = get_frames(src, args.frames)
    if not frames:
        print("No frames captured."); return None, None, []
    per_frame, ms_all = [], []
    for f in frames:
        ds, ms = detect_frame(det, f, args.upscale)
        per_frame.append(ds); ms_all.append(ms)
    res = aggregate(per_frame)
    found = [i for i in exp if i in res]
    correct = [i for i in found if res[i].answer == exp[i]]
    false_ids = sorted(i for i in res if i not in exp)
    flagged = [i for i in found if res[i].status == "review"]
    conf_wrong = [i for i in found if res[i].status == "confident" and res[i].answer != exp[i]]
    h, w = frames[-1].shape[:2]
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "distance_m": cfg["distance_m"], "marker_cm": cfg["marker_cm"], "lighting": cfg["lighting"],
        "resolution": f"{h}p", "actual_wh": f"{w}x{h}", "n_cards_expected": len(exp),
        "expected_spec": cfg["expected_spec"], "params": args.params, "upscale": args.upscale,
        "frames": len(frames), "ids_expected_found": len(found),
        "id_rate": round(len(found) / len(exp), 4), "decoded_correct": len(correct),
        "correct_rate": round(len(correct) / len(exp), 4), "false_ids": len(false_ids),
        "flagged_for_review": len(flagged), "confident_wrong": len(conf_wrong),
        "mean_ms": round(sum(ms_all) / len(ms_all), 1), "notes": cfg["notes"],
    }
    RES_DIR.mkdir(exist_ok=True)
    new = not CSV_PATH.exists()
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            wr.writeheader()
        wr.writerow(row)
    print(f"\nTRIAL: expected {len(exp)} | found {len(found)} ({row['id_rate']*100:.0f}%) | "
          f"correct {len(correct)} ({row['correct_rate']*100:.0f}%) | flagged {len(flagged)} | "
          f"CONFIDENT-but-WRONG {len(conf_wrong)} | false IDs {false_ids} | {row['mean_ms']} ms/frame")
    if conf_wrong:
        print("  !! confident-but-wrong IDs:", conf_wrong, "- these are the dangerous errors")
    missing = sorted(set(exp) - set(found))
    if missing:
        print("  not seen:", missing)
    return row, res, per_frame[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--res", default="1280x720", help="WIDTHxHEIGHT, e.g. 1920x1080")
    ap.add_argument("--image")
    ap.add_argument("--params", choices=["tuned", "default"], default="tuned")
    ap.add_argument("--upscale", type=float, default=1.0, help="try 2.0 to help small/far markers")
    ap.add_argument("--frames", type=int, default=5)
    # non-interactive trial (used for image tests / scripting)
    ap.add_argument("--distance"); ap.add_argument("--marker-cm"); ap.add_argument("--lighting")
    ap.add_argument("--expected"); ap.add_argument("--notes", default="")
    args = ap.parse_args()
    det = Detector(args.params)

    if args.image:
        img = cv2.imread(args.image)
        if img is None:
            sys.exit(f"cannot read {args.image}")
        src = {"kind": "image", "img": img}
        if args.expected:
            cfg = {"distance_m": float(args.distance or 0), "marker_cm": int(args.marker_cm or 0),
                   "lighting": args.lighting or "other", "expected_spec": args.expected, "notes": args.notes}
        else:
            cfg = setup({})
        record(src, det, cfg, args)
        return

    w, h = (int(x) for x in args.res.lower().split("x"))
    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    if not cap.isOpened():
        sys.exit("Cannot open camera. Close other apps using it, or try --camera 1")
    for _ in range(15):               # let auto-exposure/focus settle
        cap.read()
    aw, ah = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera delivers {aw}x{ah} (asked {w}x{h}). Opening preview...")
    if (aw, ah) != (w, h):
        print("  NOTE: the webcam did not give the requested size; results are labelled with the actual size.")
    src = {"kind": "cam", "cap": cap}
    cfg = setup({})
    last = None
    win = "ROOTS Camera Lab"
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        ds, _ = detect_frame(det, frame, args.upscale)
        view = draw_overlay(frame, {d.marker_id: type("R", (), {"answer": d.answer, "status": "confident" if not d.flags else "review"})() for d in ds}, ds)
        cv2.putText(view, f"{len(ds)} marker(s) | d={cfg['distance_m']}m {cfg['marker_cm']}cm {cfg['lighting']} | SPACE=trial E=edit S=snap Q=quit",
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 4)
        cv2.putText(view, f"{len(ds)} marker(s) | d={cfg['distance_m']}m {cfg['marker_cm']}cm {cfg['lighting']} | SPACE=trial E=edit S=snap Q=quit",
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 1)
        if last:
            cv2.putText(view, last, (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.imshow(win, view)
        k = cv2.waitKey(1) & 0xFF
        if k in (ord("q"), 27):
            break
        if k == ord(" "):
            row, _, _ = record(src, det, cfg, args)
            if row:
                last = f"last: found {row['id_rate']*100:.0f}%  correct {row['correct_rate']*100:.0f}%"
        elif k == ord("e"):
            cfg = setup(cfg)
        elif k == ord("s"):
            RES_DIR.joinpath("snapshots").mkdir(parents=True, exist_ok=True)
            p = RES_DIR / "snapshots" / f"snap_{datetime.now():%H%M%S}.jpg"
            cv2.imwrite(str(p), view); print("saved", p)
    cap.release(); cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

#python camera_lab.py --res 1920x1080
