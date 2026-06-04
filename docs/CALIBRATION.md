# Confidence calibration receipt

VARSITY reports a confidence in every received verdict:

```
P(verdict correct) = Phi(|M| / sigma)
```

where `M` is the measured offside margin and `sigma ~= 55 cm` is the honest broadcast-annotation
combined standard uncertainty (`services/app/uncertainty.py`; measured-anchored, see
`docs/UNCERTAINTY_SOURCES.md`). The optical-tracking equivalent (~12.7 cm, TRACAB RMSE ~9 cm per
player, Linke et al. PLOS ONE 2020) is kept only as a comparison. That confidence drives the IPCC
verbal hedge ("very likely", "about as likely as not") and the "VARSITY's Call" band that the
narration speaks.

A reported confidence is only honest if it is **calibrated**: the verdicts called "90%
confident" should be correct about 90% of the time. `services/app/calibration.py` produces
that receipt deterministically (seeded Monte-Carlo, no model call), over the *same*
`normal_cdf` the live band uses.

## The result (40,000 seeded draws, seed 11)

| Metric | Value | Reading |
|---|---|---|
| Expected Calibration Error (ECE) | **0.35%** | calibrated to within a third of a percent |
| Brier score | **0.060** | low squared error of confidence vs outcome |
| Overconfident control (sigma halved), ECE | **4.16%** | ~12x worse, the diagram discriminates |

The reliability diagram (predicted confidence on the x-axis, empirical accuracy on the y)
sits on the perfect-calibration diagonal for the well-specified model; the overconfident
control falls clearly off it. Run it live from the `/judges` page ("Run the calibration
receipt") or `GET /calibration`.

## Method

1. Draw a true (noise-free) margin `t` uniformly over +/- 0.6 m (very-tight through clear).
2. The system observes `m = t + N(0, sigma)` and reads the verdict off `m` with confidence
   `Phi(|m| / sigma)`.
3. The verdict is **correct** iff `sign(m) == sign(t)` (offside vs onside agree).
4. Bin predictions by confidence over `[0.5, 1.0]` (reported confidence is never below 0.5 , 
   the model never doubts its own verdict). ECE is the count-weighted gap between each bin's
   mean confidence and its empirical accuracy; Brier is the mean squared error of confidence
   against the {0,1} correctness outcome.

Under the stated Gaussian noise model `Phi(|M|/sigma)` is the exact Bayesian posterior, so
it is calibrated *by construction*. The receipt's job is therefore to confirm the
**implementation** realizes that property (it would catch an inverted or skewed `Phi`, the
same class of bug live-validation caught in the Guardian path) and to quantify the residual
finite-sample / binning error. The deliberately overconfident control (sigma halved) proves
the diagram is not vacuous, a miscalibrated model fails it.

## Honest scope

- This is an **implementation + self-consistency** check, not field calibration against an
  external gold-standard limb-tracked dataset. StatsBomb 360 carries a single `(x, y)` per
  player, no limb truth, so we never claim empirical calibration against real refereed
  outcomes.
- **Faithfulness != correctness.** Calibration here is about the *honesty of the reported
  confidence* in the received decision; the underlying verdict's correctness is bounded by
  the input data (stated in `docs/RESPONSIBLE_AI.md` / `docs/SAFETY_CASE.md`).
- In-concept: this describes the honesty of the confidence VARSITY reports on a received
  decision. It never adjudicates.

## Reproduce

```bash
cd services
python -m pytest tests/test_calibration.py -q
python -c "from app.calibration import calibration_payload; import json; print(json.dumps(calibration_payload(), indent=2))"
```
