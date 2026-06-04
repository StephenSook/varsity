# Uncertainty budget: the measured-source ledger

VARSITY's offside-margin uncertainty (`services/app/uncertainty.py`, `gum.py`) is a GUM Type-B
budget. This file is the **audit trail** for every number in it: which inputs are anchored to a
**measured, peer-reviewed figure**, which remain **Type-B engineering estimates**, and the exact
verbatim quote + DOI for each. It is deliberately honest about the gap.

Every source below was found by a multi-angle literature sweep and then **independently fetched and
verified** (the URL resolves, the title matches, the figure actually appears in the document). Two
candidate figures were **excluded** during verification (see "Excluded" at the end), which is the
point of doing the verification.

## The budget

The margin is `m = x_attacker - x_defender`. Its combined standard uncertainty is propagated by the
GUM law for a difference, `u_c = sqrt(u_pos^2 + U_SHAPE^2)` with
`u_pos = sqrt(u_a^2 + u_d^2 - 2*r*u_a*u_d)`:

| Input | Value | Status | Anchor |
|---|---|---|---|
| `U_COORD_BROADCAST_M` (per-point std) | 0.60 m | **MEASURED-anchored** | PnLCalib single-view projection error mean **0.65 m**; Crang 2025 detected-player RMSE **0.44-1.14 m** |
| `HOMOGRAPHY_CORRELATION` `r` | 0.70 | **Type-B (unmeasured)** | no football same-frame difference-correlation exists; partial cancellation (Szulc & Iwanowski 2026) |
| `U_SHAPE_M` (body-anchor) | 0.30 m | **partly measured** | localization floor measured (WorldPose **8 cm**, Mather **+/-10 cm**); the furthest-forward-part *selection* offset (~0.20 m) is Type-B |
| Combined `SIGMA_MARGIN_M` | **0.553 m** | derived | the point estimate; the literature places it inside a measured envelope of ~[0.26, 1.18] m |

Bottom line: the literature **corroborates** the triangulated 0.553 m almost exactly (the dominant
per-point term is now a measured 0.6-0.65 m). It is still **not** a StatsBomb-360-specific empirical
calibration against limb-tracked ground truth, because no such paired dataset exists. The two pieces
that remain genuinely unmeasured (`r` and the furthest-forward-part offset) are handled by the
**sensitivity receipt** (`gum.sigma_sensitivity`), which shows the verdict is robust across the
whole measured envelope.

## Per-point coordinate error (anchors `U_COORD_BROADCAST_M = 0.60 m`)

- **PnLCalib** (Gutierrez-Perez & Agudo, *Computer Vision and Image Understanding* 267:104712,
  2026; arXiv 2404.08401). Single-view sports-field homography, WC14-test:
  > "Proj.(m) Mean 0.65 Median 0.44" ... "the projection error was quantified as the average
  > distance, in meters, between the projected points using the estimated homography and the
  > corresponding GT ... 2500 pixels."
  With the points-and-lines step: WC14 mean 0.60, TSWC-test mean 0.23. **Verified.**
- **Crang et al. 2025** ("Concurrent validity of computer-vision AI player tracking software using
  broadcast footage", arXiv 2508.19477; FIFA-affiliated; one 2022 Qatar World Cup match vs TRACAB
  Gen5):
  > "Overall position accuracy is not currently suitable ... (RMSE = 1.68 to 16.39 m). However,
  > Providers 1 and 2 showed that ... accuracy can be suitable in this context when the player is
  > detected (RMSE = 0.44 to 1.14 m)."
  The 16.39 m end is **undetected / off-screen** players, NOT an annotated point; the **detected**
  range 0.44-1.14 m is the right regime for a visible StatsBomb 360 annotation. **Verified.**
- **Theiner et al. 2022** (WACV, DOI 10.1109/WACV51458.2022.00153). Broadcast-video extraction,
  total-system median error ~1.13 m (TC14); and
  > "Even for marginal errors in the homography estimation, i.e., ca. 95% IoU, the absolute error
  > in meter (mean) is about 1 m when backprojecting known keypoints."
  **Verified** (the ~1 m backprojection); **partial** on the median (the quote mislabeled the
  team-assignment-constraint column; the value 1.13 m is real, it is the no-constraint median).
- **AI Driven Soccer Analysis** (arXiv 2604.08722, 2026): "average projection error of 0.499
  meters" (keypoint MAE 0.225-0.26 m). **Verified** (the source says "average", not RMSE).
- **Magera et al. 2024** (CVPRW CVsports): "the differences in the estimated 3D positions can often
  exceed one meter." **Verified** (camera-model dependence, an upper-bound caution).
- **Aughey et al. 2022** (*Sports Engineering* 25:2, DOI 10.1007/s12283-021-00365-y): in-stadium CV
  vs 3D motion capture, "the mean absolute error for position was 0.15 m." **Verified** (this is the
  easier in-stadium regime, a lower bound for broadcast).

## Body-anchor / furthest-forward part (anchors `U_SHAPE_M = 0.30 m`)

- **WorldPose** (Jiang et al., CVPR 2025, arXiv 2501.02771; 2022 World Cup footage, vs Vicon):
  > "the data acquisition pipeline yields a remarkable average error per joint of 8 cm, measured
  > across global coordinates in a soccer stadium" (8.0 cm G-MPJPE). **Verified** (the metric is
  G-MPJPE; the 8 cm is exact).
- **Mather 2020** ("A Step to VAR: The Vision Science of Offside Calls", *Perception*
  49(12):1371-1374, DOI 10.1177/0301006620972006):
  > "their true positions lie at the centre of roughly Gaussian blur functions covering a distance
  > of perhaps +/- 10 cm." **Verified** (closest broadcast-TV analogue).
- **FIFA Offside Technology test report** (Second Spectrum "Dragon", report 129247, TRACK / Victoria
  University, Feb 2023): "AVERAGE X DIFFERENCE <0.10m PASS", "X,Y,Z RESULTANT DIFFERENCE <0.15m
  PASS". **Verified** as a certification *threshold* (the measured value is below it but not
  disclosed).

The `U_SHAPE_M = 0.30 m` decomposes as ~0.10 m **measured** keypoint localization plus ~0.20 m
**unmeasured** furthest-forward-part *selection* offset (the gap between a single annotated point and
the Law-11 leading limb). No study isolates that selection offset; it stays Type-B.

## Same-frame correlation `r = 0.70` (Type-B, unmeasured)

No peer-reviewed source measures the correlation between the world-projection errors of two
same-frame football points. The nearest evidence cuts *against* a clean common-mode cancel:

- **Szulc & Iwanowski 2026** (arXiv 2604.10805):
  > "the distance estimation error grows approximately quadratically with the true distance Y ...
  > homography perturbations primarily affect depth (range) estimation while leaving lateral
  > position relatively unaffected."
  So two players at different distances do **not** share an identical error; cancellation is
  **partial and geometry-dependent**. A lower `r` (wider sigma) is the more conservative reading.
  **Verified** on the range-dependence quote (the sweep's "correlation = 0" tag was a mislabel and
  is *not* used).
- The covariance-propagation machinery to compute such a correlation exists (Criminisi, Reid &
  Zisserman, "A plane measuring device", *IVC* 17(8), 1999), but reports no football number.

`r = 0.70` is therefore an explicit engineering estimate. Its uncertainty is carried by the
sensitivity envelope (`HOMOGRAPHY_CORRELATION_LO/HI = 0.50/0.85`).

## The elite-system contrast (not an input, a reference point)

- **Hawk-Eye / SAOT** (Yan 2025, ACM ICSTPA, DOI 10.1145/3796028.3796045): "it precisely identified
  even the smallest offside margin of just 1.3 centimeters." **Verified.** That ~1.3 cm is what a
  12-camera limb-tracked rig resolves; VARSITY on a single broadcast point honestly resolves ~55 cm.
  The gap *is* the honesty story.
- **Linke et al. 2020** (PLOS ONE, DOI 10.1371/journal.pone.0230179): TRACAB optical "Gen5 had ...
  better accuracy (0.08 m RMSE) ... than Gen4 (0.09 m RMSE)" vs Vicon. **Verified.** This anchors
  the optical-equivalent comparison `SIGMA_MARGIN_OPTICAL_M ~= 0.13 m`.

## Sensitivity (how robust is the conclusion?)

`gum.sigma_sensitivity(margin_m)` sweeps the **measured-literature sigma envelope** (the optimistic
end: low per-point error + strong cancellation + localization-only shape; the pessimistic end: high
per-point error + weak cancellation + full shape) and reports the confidence band at each:

- Envelope: **sigma in ~[0.26, 1.18] m**, point estimate 0.553 m sits inside.
- The clear demo call (5.69 m) reads **"clear" at every sigma in the envelope** (`band_robust`):
  the verdict does not hinge on the exact, partly-unmeasured sigma.
- A 10 cm call reads **"too close to call" at every sigma** (robustly defer).
- A 30 cm call is **not** robust (marginal at the optimistic end, too-close at the pessimistic):
  the receipt surfaces that honestly rather than hiding it behind one number.

## Excluded during verification (the honesty gate working)

- A search summary asserted "final player positioning error was below 5 meters in 91% of evaluated
  instances" for a SoccerNet paper (arXiv 2504.06357). On fetching the actual paper the sentence
  could **not** be found, so it was excluded as a likely search-engine fabrication.
- SoccerNet GSR "LocSim tau = 5 m" is a Gaussian-kernel **tolerance parameter** in the GS-HOTA
  metric, **not** a measured player-position error, so it was deliberately **not** reported as one.
- DataField.dev "limb detection 0.05-0.10 m" is a secondary blog citing FIFA with no underlying
  measurement, kept only at low confidence and not load-bearing.

## What this is, and is not

It is a **measured-anchored, sensitivity-validated** Type-B budget with a complete audit trail. It
is **not** an empirical calibration of StatsBomb 360 against limb-tracked ground truth (none
exists), and the same-frame correlation and the furthest-forward-part offset remain engineering
estimates. We say so plainly; that honesty is part of the metrology, not a hedge against it.
