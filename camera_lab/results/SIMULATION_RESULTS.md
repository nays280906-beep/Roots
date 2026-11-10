# SIMULATION RESULTS (not hardware evidence)

Synthetic frames: JPEG-compressed, blurred (sigma 0.8 px), noisy, cards held with +/-8 deg hand wobble, random A-D answers. Real webcams usually do worse (autofocus hunting, rolling shutter, uneven light). Treat every number here as a best case.

## 1. Minimum marker size the detector needs (1 card, 1080p, no tilt)

| marker side (px) | ID rate | correct-answer rate |
|---|---|---|
| 10 | 0% | 0% |
| 12 | 0% | 0% |
| 14 | 5% | 5% |
| 16 | 48% | 48% |
| 18 | 85% | 85% |
| 20 | 55% | 55% |
| 24 | 100% | 100% |
| 28 | 100% | 100% |
| 32 | 100% | 100% |
| 40 | 100% | 100% |
| 60 | 100% | 100% |
| 100 | 100% | 100% |

**Smallest size passing 95% ID / 90% decode in simulation: 24 px.** Results below ~24 px are noisy and not monotonic: the synthetic marker uses integer-pixel cells, so some sizes resample badly. Read it as "below ~24 px is unreliable", not as an exact curve.

## 2. Stress at a comfortable size vs the minimum (1 card, 40 trials each)

| condition | side px | ID rate | correct rate |
|---|---|---|---|
| clean | 32 | 100% | 100% |
| tilt 30 deg | 32 | 100% | 100% |
| tilt 45 deg | 32 | 100% | 100% |
| dim room (whole scene x0.35) | 32 | 100% | 100% |
| bright room (whole scene x1.3) | 32 | 100% | 100% |
| glare blob 0.8 | 32 | 0% | 0% |
| blur sigma 1.6 | 32 | 65% | 65% |
| blur sigma 2.4 | 32 | 0% | 0% |
| motion blur 7px | 32 | 8% | 8% |
| clean | 44 | 100% | 100% |
| tilt 30 deg | 44 | 100% | 100% |
| tilt 45 deg | 44 | 100% | 100% |
| dim room (whole scene x0.35) | 44 | 100% | 100% |
| bright room (whole scene x1.3) | 44 | 100% | 100% |
| glare blob 0.8 | 44 | 0% | 0% |
| blur sigma 1.6 | 44 | 100% | 100% |
| blur sigma 2.4 | 44 | 2% | 2% |
| motion blur 7px | 44 | 98% | 98% |

## 3. Many cards in one frame (cards big enough; tests logic + CPU time only)

| cards | side px | ID rate | correct rate | false IDs | ms/frame |
|---|---|---|---|---|---|
| 1 | 38 | 100% | 100% | 0 | 22 |
| 5 | 38 | 100% | 100% | 0 | 23 |
| 10 | 38 | 100% | 100% | 0 | 23 |
| 20 | 38 | 100% | 100% | 0 | 27 |
| 30 | 38 | 100% | 100% | 0 | 29 |
| 40 | 38 | 100% | 100% | 0 | 39 |

## 4. Geometry: predicted marker size in pixels (calculation, not measurement)

Rule from section 1: need roughly **>= 32 px** for margin. side_px = f_px * size_m / distance, f_px = (W/2)/tan(HFOV/2). Marker held head-on; real cards are held at an angle and partly covered.


**720p, HFOV 60 deg** (frame width at 6 m = 6.9 m)

| marker | 1 m | 2 m | 3 m | 4 m | 5 m | 6 m | 7 m |
|---|---|---|---|---|---|---|---|
| 10 cm | 111 OK | 55 OK | 37 OK | 28 edge | 22 FAIL | 18 FAIL | 16 FAIL |
| 15 cm | 166 OK | 83 OK | 55 OK | 42 OK | 33 OK | 28 edge | 24 FAIL |
| 20 cm | 222 OK | 111 OK | 74 OK | 55 OK | 44 OK | 37 OK | 32 edge |

**720p, HFOV 78 deg** (frame width at 6 m = 9.7 m)

| marker | 1 m | 2 m | 3 m | 4 m | 5 m | 6 m | 7 m |
|---|---|---|---|---|---|---|---|
| 10 cm | 79 OK | 40 OK | 26 edge | 20 FAIL | 16 FAIL | 13 FAIL | 11 FAIL |
| 15 cm | 119 OK | 59 OK | 40 OK | 30 edge | 24 FAIL | 20 FAIL | 17 FAIL |
| 20 cm | 158 OK | 79 OK | 53 OK | 40 OK | 32 edge | 26 edge | 23 FAIL |

**1080p, HFOV 60 deg** (frame width at 6 m = 6.9 m)

| marker | 1 m | 2 m | 3 m | 4 m | 5 m | 6 m | 7 m |
|---|---|---|---|---|---|---|---|
| 10 cm | 166 OK | 83 OK | 55 OK | 42 OK | 33 OK | 28 edge | 24 FAIL |
| 15 cm | 249 OK | 125 OK | 83 OK | 62 OK | 50 OK | 42 OK | 36 OK |
| 20 cm | 333 OK | 166 OK | 111 OK | 83 OK | 67 OK | 55 OK | 48 OK |

**1080p, HFOV 78 deg** (frame width at 6 m = 9.7 m)

| marker | 1 m | 2 m | 3 m | 4 m | 5 m | 6 m | 7 m |
|---|---|---|---|---|---|---|---|
| 10 cm | 119 OK | 59 OK | 40 OK | 30 edge | 24 FAIL | 20 FAIL | 17 FAIL |
| 15 cm | 178 OK | 89 OK | 59 OK | 44 OK | 36 OK | 30 edge | 25 edge |
| 20 cm | 237 OK | 119 OK | 79 OK | 59 OK | 47 OK | 40 OK | 34 OK |

OK = above minimum+8 px margin; edge = between minimum and margin; FAIL = below minimum.