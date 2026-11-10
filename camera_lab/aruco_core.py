"""
ROOTS M0 - ArUco core: detection, orientation decoding, burst voting.

Standalone (OpenCV + NumPy only). No ROOTS dependencies, no database, no
network. Frames are processed in memory and never written to disk here.

CARD CONVENTION (what the student does)
    The student holds the card so that the letter of their answer is at the TOP.
    Letters are printed on the card edges as:  A = top, B = left, C = bottom, D = right.
    So, seen from the camera, the marker is rotated clockwise by:
        0 deg -> A      90 deg -> B      180 deg -> C      270 deg -> D
    (B is printed on the LEFT edge because rotating the card 90 deg clockwise
     carries the left edge to the top.)
"""
from __future__ import annotations
import math, time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import cv2
import numpy as np

DICT_NAME = "DICT_4X4_50"
LETTERS = "ABCD"

# Thresholds (all tunable; documented in FEASIBILITY_RESULTS.md)
MIN_SIDE_PX = 24          # marker edge shorter than this -> "small_marker" flag
ANGLE_OK_DEG = 20         # within +/-20 deg of a cardinal direction = clean
ANGLE_AMBIG_DEG = 35      # beyond +/-35 deg = ambiguous, must be reviewed
MIN_AGREE = 0.6           # burst voting: share of frames agreeing on the letter
MIN_SEEN = 0.4            # burst voting: share of frames in which the ID appeared


def _dictionary():
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICT_NAME))


class Detector:
    """Thin wrapper hiding the OpenCV 4.6 / 4.7+ ArUco API difference."""

    def __init__(self, params: str = "tuned"):
        self.dict = _dictionary()
        self.params_name = params
        if hasattr(cv2.aruco, "ArucoDetector"):            # OpenCV >= 4.7
            p = cv2.aruco.DetectorParameters()
            self._new_api = True
        else:                                              # legacy
            p = cv2.aruco.DetectorParameters_create()
            self._new_api = False
        if params == "tuned":
            p.adaptiveThreshWinSizeMin = 3
            p.adaptiveThreshWinSizeMax = 53
            p.adaptiveThreshWinSizeStep = 10
            p.minMarkerPerimeterRate = 0.01   # allow small/far markers
            p.polygonalApproxAccuracyRate = 0.05
            p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.p = p
        if self._new_api:
            self.det = cv2.aruco.ArucoDetector(self.dict, p)

    def raw(self, gray):
        if self._new_api:
            corners, ids, _ = self.det.detectMarkers(gray)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(gray, self.dict, parameters=self.p)
        return corners, ids


@dataclass
class Detection:
    marker_id: int
    answer: str                 # 'A'..'D'
    angle_deg: float            # clockwise rotation, 0..360
    off_cardinal_deg: float     # signed distance to nearest cardinal angle
    side_px: float              # mean edge length of the marker in pixels
    center: tuple
    corners: np.ndarray
    flags: list = field(default_factory=list)


def decode_orientation(corners4: np.ndarray):
    """Return (angle_deg_cw, letter, off_cardinal). corners4: 4x2, ArUco order TL,TR,BR,BL."""
    c = np.asarray(corners4, dtype=float).reshape(4, 2)
    v = (c[1] - c[0]) + (c[2] - c[3])            # average of top and bottom edge vectors
    ang = math.degrees(math.atan2(v[1], v[0])) % 360     # image y is down => clockwise
    idx = int(((ang + 45) % 360) // 90)
    off = ((ang + 45) % 90) - 45
    return ang, LETTERS[idx], off


def detect_frame(detector: Detector, frame, upscale: float = 1.0):
    """Detect in one frame. Returns (list[Detection], elapsed_ms)."""
    t0 = time.perf_counter()
    gray = frame if frame.ndim == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if upscale and upscale != 1.0:
        gray = cv2.resize(gray, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    corners, ids = detector.raw(gray)
    out = []
    if ids is not None:
        for c, i in zip(corners, ids.flatten()):
            c4 = c.reshape(4, 2) / (upscale or 1.0)
            ang, letter, off = decode_orientation(c4)
            side = float(np.mean([np.linalg.norm(c4[k] - c4[(k + 1) % 4]) for k in range(4)]))
            d = Detection(int(i), letter, ang, off, side, tuple(c4.mean(axis=0)), c4)
            if side < MIN_SIDE_PX:
                d.flags.append("small_marker")
            if abs(off) > ANGLE_AMBIG_DEG:
                d.flags.append("ambiguous_angle")
            elif abs(off) > ANGLE_OK_DEG:
                d.flags.append("low_angle_margin")
            out.append(d)
    # same ID seen twice in ONE frame -> two physical cards share an ID
    counts = Counter(d.marker_id for d in out)
    for d in out:
        if counts[d.marker_id] > 1:
            d.flags.append("duplicate_id")
    return out, (time.perf_counter() - t0) * 1000.0


@dataclass
class VotedResult:
    marker_id: int
    answer: str
    agree: float        # share of sightings that voted for `answer`
    seen: float         # share of frames in which this ID appeared
    mean_side_px: float
    flags: list
    status: str         # 'confident' | 'review'


def aggregate(frames_dets: list[list[Detection]]) -> dict[int, VotedResult]:
    """Vote across a burst of frames. Anything not clean becomes 'review' (never auto-accepted)."""
    n = max(len(frames_dets), 1)
    by_id = defaultdict(list)
    for dets in frames_dets:
        for d in dets:
            by_id[d.marker_id].append(d)
    res = {}
    for mid, ds in by_id.items():
        votes = Counter(d.answer for d in ds)
        ans, cnt = votes.most_common(1)[0]
        agree, seen = cnt / len(ds), len(ds) / n
        flags = set()
        for d in ds:
            if d.answer == ans:
                flags.update(d.flags)
        if agree < MIN_AGREE:
            flags.add("inconsistent")
        if seen < MIN_SEEN:
            flags.add("seen_rarely")
        res[mid] = VotedResult(mid, ans, agree, seen,
                               float(np.mean([d.side_px for d in ds])),
                               sorted(flags), "review" if flags else "confident")
    return res


# ---- helpers used by tools ----
def marker_matrix(marker_id: int) -> np.ndarray:
    """6x6 matrix (1=black) of the marker incl. its 1-cell black border."""
    d = _dictionary()
    if hasattr(cv2.aruco, "generateImageMarker"):
        img = cv2.aruco.generateImageMarker(d, marker_id, 6)
    else:
        img = cv2.aruco.drawMarker(d, marker_id, 6)
    return (img < 128).astype(np.uint8)


def draw_overlay(frame, results: dict[int, VotedResult], last_dets: list[Detection]):
    out = frame.copy()
    for d in last_dets:
        r = results.get(d.marker_id)
        col = (80, 200, 120) if (r and r.status == "confident") else (0, 165, 255)
        pts = d.corners.astype(int).reshape(-1, 1, 2)
        cv2.polylines(out, [pts], True, col, 3)
        x, y = int(d.center[0]), int(d.center[1])
        label = f"#{d.marker_id}={r.answer if r else d.answer}"
        cv2.putText(out, label, (x - 30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(out, label, (x - 30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, col, 2)
    return out
