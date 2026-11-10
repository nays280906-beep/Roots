# ROOTS M0 - Camera Feasibility Lab

Goal: find out, with YOUR webcam and a real room, how far and how many cards the camera can read.
Nothing here is the final ROOTS camera module. It's a measuring instrument.

## What has and has not been verified
| Verified (in a sandbox, no camera) | NOT verified (needs you) |
|---|---|
| Orientation decoding A/B/C/D is correct for all 50 marker IDs (cv2.rotate cross-check) | Anything about your webcam, lens, autofocus |
| Printed PDF -> detect round trip: 120/120 | Real lighting, glare, motion blur from hands |
| Works on OpenCV 4.10 and 5.0 | Real distance limits, real crowd limits |
| Simulation: detector needs about 24+ px marker side; blur is the main killer; glare over the marker is fatal | The live-preview window of `camera_lab.py` (written, compile-checked, never run with a camera) |

If `camera_lab.py` crashes on your laptop, send me the error. That is a bug in my untested part.

## 1. Install (Windows, PowerShell, in this folder)
```
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
(`python` instead of `py -3.11` works if that is how Python is installed.)

## 2. Print cards
```
python make_test_sheets.py                # sheets\roots_cards_10cm.pdf, 15cm, 20cm  (ids 0-9)
python make_test_sheets.py --ids 0-29 --sizes 15
```
- 10 cm marker = A5 card, 15 cm = A4, 20 cm = A3 (print shop).
- Print at **100% / Actual size**, never "Fit to page". Measure the 5 cm bar with a ruler. If it is not 5 cm, the distance maths is wrong.
- **Matte paper only.** Glossy paper causes glare that blanks the marker.
- Letters: A top, B left, C bottom, D right. **Hold the card so your answer letter is at the TOP.**

## 3. Measure
Put the webcam where it will really sit (front of room, ideally raised). Measure the distance to the first, middle and last rows with a tape. Note the camera's field of view if known.

```
python camera_lab.py --res 1920x1080
```
The tool asks for the conditions, shows the live view, and SPACE records a trial (5 frames, about 1 second).
If the camera gives a different size than requested, it says so and results are labelled with the real size.

### Minimum protocol (about 30 trials, 45 minutes)
Each trial = everyone holds the cards at the stated answers. Use `0-4:A` style (all five cards held at A) and vary the answer between trials.

| Step | What | Trials |
|---|---|---|
| 1 | **Distance sweep**: 1 card, 15 cm marker, normal light, at 1, 2, 3, 4, 5, 6, 7 m (or as far as your room goes), answer A | 7 |
| 2 | **Orientation**: at the farthest distance that passed in step 1, same card held A, B, C, D | 4 |
| 3 | **Tilt**: same distance, card tilted about 15, 30, 45 degrees (note it in Notes) | 3 |
| 4 | **Marker size**: 10 cm and 20 cm at that same distance | 2-4 |
| 5 | **Lighting** (15 cm, same distance): bright, dim (lights off, curtains drawn), window behind the card holder, glare (tilt the card toward a light) | 4-8 |
| 6 | **Crowd**: 5, 10, 20, 30 cards in frame at the target distance (use friends/colleagues, or lay cards on chairs). Mixed answers: `0-4:A,5-9:B,...` | 4-8 |
| 7 | **Hands covering**: the same crowd, but people hold the card at the edges with fingers over the corners | 2 |
| 8 | **720p vs 1080p**: repeat step 6 with `--res 1280x720` | 2-4 |

Then:
```
python report.py --class-size 30 --target-distance 5 --target-size 15
```
This writes `FEASIBILITY_RESULTS.md`. Send me that file and `results\trials.csv`.

### Pass rule (adjust if you disagree)
Per condition: ID rate >= 95%, correct answer >= 90%, and **zero confident-but-wrong** results.
"Confident-but-wrong" is the dangerous error: the system would have accepted a wrong answer without asking the teacher. A missed card is acceptable (it goes to the review list); a confidently wrong card is not.

## Scan modes (decided from your results, built in M5)
1. **Full-class**: only if the report shows the full class count passing at the real seating distance.
2. **Group-wise** (default assumption): rows or groups hold cards up in turn. Group size comes from the report.
3. **Cumulative**: several scans of one question merge, so only the missed students are re-scanned.
4. **Manual**: one tap per student, always available.

## Tuning options to try if results are poor
- `--upscale 2` (helps small, far markers; slower)
- `--params default` vs `tuned` (compare)
- Bigger cards, a camera nearer the class, a wider-angle or 1080p camera, manual focus if the camera allows
- Scanning in two halves of the room

## Privacy
Nothing is written to disk except trial numbers in `results\trials.csv`. Snapshots only if you press S. Don't save pictures of children.

## Files
`aruco_core.py` detector and decoding | `make_test_sheets.py` printable cards | `camera_lab.py` measuring tool |
`report.py` results report | `synthetic_test.py` simulation | `results\SIMULATION_RESULTS.md` simulated numbers
