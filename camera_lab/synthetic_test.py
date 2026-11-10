"""
ROOTS M0 - SIMULATION ONLY. Validates decoding logic and estimates the minimum
marker size (in pixels) our detector needs. It does NOT measure any real webcam,
lens, lighting or classroom. Real numbers come from camera_lab.py.
"""
import math, random, time
from pathlib import Path
import cv2, numpy as np
from aruco_core import Detector, detect_frame, marker_matrix, LETTERS

random.seed(7); np.random.seed(7)
DET = Detector("tuned")


def marker_img(mid, side_px):
    """Black-square marker with a white quiet zone of 1 cell, at ~side_px for the black square."""
    cell = max(side_px / 6.0, 1.0)
    m = marker_matrix(mid)
    n = int(round(cell * 6))
    big = cv2.resize((1 - m) * 255, (n, n), interpolation=cv2.INTER_NEAREST).astype(np.uint8)
    q = int(round(cell))
    return cv2.copyMakeBorder(big, q, q, q, q, cv2.BORDER_CONSTANT, value=255), q


def place(scene, mid, side_px, cx, cy, rot_cw, tilt_deg=0, brightness=1.0, glare=0.0):
    img, q = marker_img(mid, side_px)
    h, w = img.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), -rot_cw, 1.0)    # negative = clockwise
    # perspective-ish tilt by squeezing horizontally (card turned away from camera)
    img = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_AREA, borderValue=255)
    if tilt_deg:
        sx = math.cos(math.radians(tilt_deg))
        img = cv2.resize(img, (max(int(w * sx), 2), h), interpolation=cv2.INTER_AREA)
        h, w = img.shape
    img = (img.astype(np.float32) * brightness)
    if glare > 0:                                                  # saturated blob over part of the card
        yy, xx = np.mgrid[0:h, 0:w]
        blob = np.exp(-(((xx - w * .35) / (w * .28)) ** 2 + ((yy - h * .4) / (h * .22)) ** 2))
        img = img + glare * 255 * blob
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    H, W = scene.shape
    x1, y1 = max(x0, 0), max(y0, 0)
    x2, y2 = min(x0 + w, W), min(y0 + h, H)
    if x2 > x1 and y2 > y1:
        scene[y1:y2, x1:x2] = np.clip(img[y1 - y0:y2 - y0, x1 - x0:x2 - x0], 0, 255)


def degrade(scene, blur=0.8, noise=3.0, jpeg=75, motion=0):
    s = scene
    if motion:
        k = np.zeros((motion, motion), np.float32); k[motion // 2, :] = 1.0 / motion
        s = cv2.filter2D(s, -1, k)
    if blur > 0:
        s = cv2.GaussianBlur(s, (0, 0), blur)
    s = np.clip(s.astype(np.float32) + np.random.normal(0, noise, s.shape), 0, 255).astype(np.uint8)
    ok, enc = cv2.imencode(".jpg", s, [cv2.IMWRITE_JPEG_QUALITY, jpeg])
    return cv2.imdecode(enc, cv2.IMREAD_GRAYSCALE)


def run_cards(n_cards, side_px, W=1920, H=1080, rots=None, tilt=0, bright=1.0, glare=0.0,
              blur=0.8, noise=3.0, motion=0, bg=170):
    """One synthetic frame with n_cards on a grid. Returns (id_rate, correct_rate, false_pos, ms)."""
    scene = np.full((H, W), bg, np.uint8)
    cols = int(math.ceil(math.sqrt(n_cards * W / H)))
    rows = int(math.ceil(n_cards / cols))
    cw, ch = W / cols, H / rows
    truth = {}
    for i in range(n_cards):
        r, c = divmod(i, cols)
        ans = random.choice(LETTERS) if rots is None else rots
        rot = LETTERS.index(ans) * 90 + random.uniform(-8, 8)   # a hand never holds it perfectly
        place(scene, i, side_px, (c + .5) * cw, (r + .5) * ch, rot, tilt, 1.0, glare)
        truth[i] = ans
    scene = np.clip(scene.astype(np.float32) * bright, 0, 255).astype(np.uint8)  # whole-room light level
    frame = degrade(scene, blur, noise, motion=motion)
    ds, ms = detect_frame(DET, frame)
    seen = {d.marker_id: d.answer for d in ds}
    found = sum(1 for k in truth if k in seen)
    correct = sum(1 for k in truth if seen.get(k) == truth[k])
    fp = sum(1 for k in seen if k not in truth)
    return found / n_cards, correct / n_cards, fp, ms


def rate(n_cards, side_px, trials=6, **kw):
    r = [run_cards(n_cards, side_px, **kw) for _ in range(trials)]
    return (np.mean([x[0] for x in r]), np.mean([x[1] for x in r]),
            sum(x[2] for x in r), np.mean([x[3] for x in r]))


def main():
    out = []
    P = out.append
    P("# SIMULATION RESULTS (not hardware evidence)\n")
    P("Synthetic frames: JPEG-compressed, blurred (sigma 0.8 px), noisy, cards held with +/-8 deg hand wobble, "
      "random A-D answers. Real webcams usually do worse (autofocus hunting, rolling shutter, uneven light). "
      "Treat every number here as a best case.\n")

    # 1 minimum pixel size
    P("## 1. Minimum marker size the detector needs (1 card, 1080p, no tilt)\n")
    P("| marker side (px) | ID rate | correct-answer rate |\n|---|---|---|")
    sizes = [10, 12, 14, 16, 18, 20, 24, 28, 32, 40, 60, 100]
    min95 = None
    for s in sizes:
        a, b, _, _ = rate(1, s, trials=40)
        P(f"| {s} | {a*100:.0f}% | {b*100:.0f}% |")
        if min95 is None and a >= .95 and b >= .90:
            min95 = s
    P(f"\n**Smallest size passing 95% ID / 90% decode in simulation: {min95} px.** Results below ~24 px are noisy and not monotonic: the synthetic marker uses integer-pixel cells, so some sizes resample badly. Read it as \"below ~24 px is unreliable\", not as an exact curve.\n")
    margin = None
    # 2 with tilt / blur / glare / dim
    P("## 2. Stress at a comfortable size vs the minimum (1 card, 40 trials each)\n")
    P("| condition | side px | ID rate | correct rate |\n|---|---|---|---|")
    for s in (min95 + 8, min95 + 20):
        for name, kw in [("clean", {}), ("tilt 30 deg", dict(tilt=30)), ("tilt 45 deg", dict(tilt=45)),
                         ("dim room (whole scene x0.35)", dict(bright=.35)), ("bright room (whole scene x1.3)", dict(bright=1.3)),
                         ("glare blob 0.8", dict(glare=.8)), ("blur sigma 1.6", dict(blur=1.6)),
                         ("blur sigma 2.4", dict(blur=2.4)), ("motion blur 7px", dict(motion=7))]:
            a, b, _, _ = rate(1, s, trials=40, **kw)
            P(f"| {name} | {s} | {a*100:.0f}% | {b*100:.0f}% |")

    # 3 crowd
    P("\n## 3. Many cards in one frame (cards big enough; tests logic + CPU time only)\n")
    P("| cards | side px | ID rate | correct rate | false IDs | ms/frame |\n|---|---|---|---|---|---|")
    for n in (1, 5, 10, 20, 30, 40):
        s = min(min95 + 14, int(1080 / max(math.ceil(n ** .5), 1) * .5))
        a, b, fp, ms = rate(n, s, trials=6)
        P(f"| {n} | {s} | {a*100:.0f}% | {b*100:.0f}% | {fp} | {ms:.0f} |")

    # 4 geometry
    P("\n## 4. Geometry: predicted marker size in pixels (calculation, not measurement)\n")
    P(f"Rule from section 1: need roughly **>= {min95 + 8} px** for margin. "
      "side_px = f_px * size_m / distance, f_px = (W/2)/tan(HFOV/2). "
      "Marker held head-on; real cards are held at an angle and partly covered.\n")
    for W, label in ((1280, "720p"), (1920, "1080p")):
        for hfov in (60, 78):
            f = (W / 2) / math.tan(math.radians(hfov / 2))
            P(f"\n**{label}, HFOV {hfov} deg** (frame width at 6 m = {2*6*math.tan(math.radians(hfov/2)):.1f} m)\n")
            P("| marker | " + " | ".join(f"{d} m" for d in range(1, 8)) + " |\n|---|" + "---|" * 7)
            for cmz in (10, 15, 20):
                cells = []
                for d in range(1, 8):
                    px = f * (cmz / 100) / d
                    mark = "OK" if px >= min95 + 8 else ("edge" if px >= min95 else "FAIL")
                    cells.append(f"{px:.0f} {mark}")
                P(f"| {cmz} cm | " + " | ".join(cells) + " |")
    P("\nOK = above minimum+8 px margin; edge = between minimum and margin; FAIL = below minimum.")
    Path("results").mkdir(exist_ok=True)
    Path("results/SIMULATION_RESULTS.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    t = time.time(); main(); print(f"\n(done in {time.time()-t:.0f}s)")
