"""
Generate printable ROOTS test cards (vector PDF, DICT_4X4_50).

    python make_test_sheets.py                 -> ids 0-9, sizes 10/15/20 cm
    python make_test_sheets.py --ids 0-29 --sizes 15

"Marker size" = the side of the BLACK square, not the card.
  10 cm marker -> A5 card   |  15 cm -> A4 card  |  20 cm -> A3 card
PRINT AT 100% / "Actual size" (NOT "Fit to page"). Check the 5 cm bar with a ruler.
Use matte paper: glossy card causes glare.

Letters are on the card edges: A top, B left, C bottom, D right.
Hold the card so your answer letter is at the TOP.
"""
import argparse
from pathlib import Path
from reportlab.lib.pagesizes import A3, A4, A5
from reportlab.lib.units import cm
from reportlab.lib.colors import black, white, HexColor
from reportlab.pdfgen import canvas
from aruco_core import marker_matrix, DICT_NAME

PAGE = {10: A5, 15: A4, 20: A3}
PASTEL = {"A": "#B8EBD0", "B": "#BFE3F7", "C": "#FFF0A8", "D": "#DCCBF5"}


def parse_ids(s):
    ids = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-"); ids += list(range(int(a), int(b) + 1))
        else:
            ids.append(int(part))
    return ids


def draw_letter(c, letter, cx, cy, rot, r):
    c.saveState()
    c.translate(cx, cy); c.rotate(rot)
    c.setFillColor(HexColor(PASTEL[letter])); c.setStrokeColor(black); c.setLineWidth(1.2)
    c.circle(0, 0, r, fill=1, stroke=1)
    c.setFillColor(black); c.setFont("Helvetica-Bold", r * 1.35)
    c.drawCentredString(0, -r * 0.47, letter)
    c.restoreState()


def draw_card(c, marker_id, size_cm, pagesize):
    W, H = pagesize
    S = size_cm * cm
    cell = S / 6
    x0, y0 = (W - S) / 2, (H - S) / 2
    m = marker_matrix(marker_id)
    c.setFillColor(white); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(black)
    for r in range(6):
        for k in range(6):
            if m[r, k]:
                # +0.2pt overlap avoids hairline gaps between cells in some viewers
                c.rect(x0 + k * cell, y0 + (5 - r) * cell, cell + 0.2, cell + 0.2, fill=1, stroke=0)
    mx, my = (W - S) / 2, (H - S) / 2        # margins
    rad = min(mx, my) * 0.30
    rad = min(rad, 1.3 * cm)
    # A top, B left, C bottom, D right  (B left => rotating card 90deg CW puts B on top)
    draw_letter(c, "A", W / 2, y0 + S + my / 2, 0, rad)
    draw_letter(c, "B", mx / 2, H / 2, 90, rad)
    draw_letter(c, "C", W / 2, my / 2, 180, rad)
    draw_letter(c, "D", x0 + S + mx / 2, H / 2, -90, rad)
    # info + print-scale check bar (5 cm) in the bottom-left margin corner
    c.setFont("Helvetica", 8); c.setFillColor(black)
    c.drawString(0.8 * cm, 0.9 * cm, f"ROOTS test card  ID {marker_id:02d}   marker {size_cm} cm   {DICT_NAME}")
    c.setLineWidth(2); c.line(0.8 * cm, 0.55 * cm, 0.8 * cm + 5 * cm, 0.55 * cm)
    for t in range(6):
        c.line(0.8 * cm + t * cm, 0.4 * cm, 0.8 * cm + t * cm, 0.7 * cm)
    c.drawString(0.8 * cm + 5.2 * cm, 0.5 * cm, "<- this bar must measure 5 cm")


def build(ids, size_cm, out: Path):
    ps = PAGE[size_cm]
    c = canvas.Canvas(str(out), pagesize=ps)
    c.setTitle(f"ROOTS test cards {size_cm}cm")
    for mid in ids:
        draw_card(c, mid, size_cm, ps); c.showPage()
    c.save()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="0-9")
    ap.add_argument("--sizes", default="10,15,20")
    ap.add_argument("--out", default="sheets")
    a = ap.parse_args()
    Path(a.out).mkdir(exist_ok=True)
    for s in parse_ids(a.sizes.replace(" ", "")):
        if s not in PAGE:
            raise SystemExit(f"size must be one of {list(PAGE)}")
        p = Path(a.out) / f"roots_cards_{s}cm.pdf"
        build(parse_ids(a.ids), s, p)
        print("wrote", p)
