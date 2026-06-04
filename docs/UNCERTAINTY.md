# The uncertainty budget: GUM, Bayesian, and information-theoretic

VARSITY reports an offside margin. That number is an estimate from coarse data, so the
honest thing is to say *how* coarse, the way international metrology does. `services/app/gum.py`
is the rigorous superset of the "VARSITY's Call" band (`uncertainty.py`): a GUM-compliant
uncertainty budget, a Bayesian credible interval, the Shannon entropy of the call in bits,
and a Monte-Carlo cross-check. It **describes** the precision of the received decision's
geometry; it never adjudicates.

## The honest two-regime picture

Our coordinates are a single **broadcast-annotated** `(x, y)` per player from StatsBomb 360, 
not limb-level optical tracking. So there are two regimes, and we report both:

- **Broadcast-annotation (honest, what the band reports):** on the single annotated point we
  actually have, the coordinate uncertainty is far larger. The same-frame homography systematic
  error **partially cancels** in the differential margin, but the residual plus the body-anchor
  shape uncertainty give a combined standard uncertainty `sigma ~= 0.55 m` and an honest expanded
  uncertainty of ~1.1 m at 95% coverage. This is what the "VARSITY's Call" band, the structured
  `p_verdict`, and the calibration receipt (`/calibration`) all use.
- **Optical-equivalent (the comparison only):** if this were TRACAB-grade optical tracking (~9 cm
  per player, Linke et al., *PLOS ONE* 2020), the margin would be good to ~13 cm. That figure is
  kept **only** as the "if we had a 12-camera SAOT rig" comparison, never as the data's uncertainty
  (a semi-automated rig resolves ~1.3 cm offside margins; Yan 2025).

VARSITY leads with the honest regime. The point of the report (the Innovation angle) is that
**our coarse data correctly refuses to pretend to centimetre precision.**

## The GUM budget (BIPM JCGM 100:2008)

The margin is `m = x_attacker - x_defender`. Its combined standard uncertainty follows the GUM
law of propagation for a **difference** (Eq. 16 with sensitivity coefficients +1, -1):

```
u_c²(m) = u_a² + u_d² - 2·r·u_a·u_d
```

The **minus** sign is correct for a subtraction: positive correlation `r` (shared common-mode
homography error) *reduces* the combined uncertainty, because that error cancels. The
body-anchor shape uncertainty (IFAB Law 11 measures the furthest-forward body part, not the
annotated point) adds in quadrature. The **expanded uncertainty** is `U = k·u_c` with coverage
factor `k = 2`, which gives **approximately 95%** coverage *for an approximately-normal
distribution with large effective degrees of freedom* (GUM clause 6.3.3; the exact
asymptotic-normal value is 95.45%). The **coverage interval** is `m ± U`.

The inputs (in `uncertainty.py`), now anchored to **measured, fetch-verified** figures where one
exists (full verbatim ledger: `docs/UNCERTAINTY_SOURCES.md`):

| Input | Value | Status + basis |
|---|---|---|
| `U_COORD_BROADCAST_M` | 0.60 m per coordinate | **MEASURED-anchored:** single-view projection error mean 0.65 m (PnLCalib, *CVIU* 2026); detected-player RMSE 0.44-1.14 m (Crang et al. 2025, arXiv 2508.19477) |
| `HOMOGRAPHY_CORRELATION` `r` | 0.70 | **Type-B (unmeasured):** partial same-frame cancellation; homography error is range-dependent (Szulc & Iwanowski 2026), so a lower `r` is more conservative |
| `U_SHAPE_M` | 0.30 m | **partly measured:** ~0.10 m localization floor (WorldPose 8 cm, *CVPR* 2025; Mather +/-10 cm, 2020) + ~0.20 m unmeasured furthest-forward-part offset |
| `K_COVERAGE` `k` | 2 | ~95% coverage (normal, large DoF) |

Each input is anchored to a measured figure where one exists; the genuinely unmeasured pieces (`r`,
the furthest-forward-part offset) are flagged Type-B and carried by the **sensitivity receipt**
below. This remains **not** a StatsBomb-360-specific calibration against limb-tracked ground truth
(none exists). We say so plainly; that honesty is part of the metrology, not a hedge against it.

### Sigma sensitivity (the measured envelope)

`gum.sigma_sensitivity(m)` (and `GET /uncertainty`, extended) sweeps the **measured-literature
sigma envelope** ~[0.26, 1.18] m (optimistic: low per-point error, strong cancellation,
localization-only shape; pessimistic: the reverse) and reports the confidence band at each sigma.
The clear demo call (5.69 m) reads **clear at every sigma** in the envelope, so the verdict does not
hinge on the exact, partly-unmeasured sigma; a 10 cm call is **too-close at every sigma**; a 30 cm
call is **not** robust (marginal-to-too-close), which the receipt surfaces honestly. This converts a
single-point sigma into a range-validated claim.

## Bayesian posterior + credible interval

Under the maximum-entropy Gaussian noise model (below), the posterior on the margin is Gaussian,
so `P(offside | data) = Φ(m / σ_m)` is a one-line, closed-form computation (no MCMC), and the
95% **credible interval** is `m ± 1.96·σ_m`. This admits the probabilistic statement a frequentist
interval cannot: "there is 95% posterior probability the true margin lies in this interval."

## Shannon entropy → narration verbosity

The Shannon binary entropy `H₂(p) = -p·log₂p - (1-p)·log₂(1-p)` in **bits** is the honest measure
of how uncertain the call is: 1 bit at `p = 0.5` (a coin flip), 0 bits at a certain call. It
**drives narration length**: under ~0.2 bits → concise, under ~0.7 bits → standard, otherwise
the full hedged narration ("rich"). More bits of uncertainty, more words.

## Maximum entropy + temperature (Jaynes 1957; Guo et al. 2017)

The Gaussian noise model is not arbitrary: given only a known variance, the Gaussian is the
**maximum-entropy** distribution (Jaynes, *Phys. Rev.* 106:620, 1957; Cover & Thomas, Thm 8.6.5;
GUM Supplement 1), the least-committal choice that respects what we know. The margin-to-probability
map `P = Φ(m/σ_m)` is exactly the Boltzmann/softmax at temperature `T = σ_m / 1.7` (since
`Φ ≈ logistic(1.7·x)`; Guo, Pleiss, Sun & Weinberger, ICML 2017). `T` has a physical narration:
"about a quarter of a metre, within that range the call is genuinely uncertain."

## Monte-Carlo cross-check (JCGM 101:2008)

`monte_carlo_p_offside` propagates the noise by sampling (GUM Supplement 1, the Monte-Carlo
method): "in N of 10,000 perturbed draws the attacker was beyond the line." It agrees with the
closed-form `Φ` (a Technical-Execution cross-check) and is far more intuitive for a blind-fan
narration and a demo. A Wilson 95% interval bounds the simulation proportion.

## What this is, and is not

- It is an **implementation + budget**, surfaced live at `GET /uncertainty` and as the
  `uncertainty_budget` SSE stage. The tight demo scenario (0.02 m) has a coverage interval that
  **straddles zero** (`[-1.09, +1.13] m`), honestly too close to call, with ~1.0 bit of entropy;
  the clear scenarios stay clear with ~0 bits.
- It is **not** field calibration against limb-tracked ground truth (StatsBomb 360 has none). The
  budget is now **measured-anchored** where the literature allows (`docs/UNCERTAINTY_SOURCES.md`);
  the same-frame correlation and the furthest-forward-part offset remain documented Type-B estimates.
- It **describes** the received decision's geometric precision. It never re-adjudicates the call.

## Robustness receipts (`GET /uncertainty`, extended; `GET /calibration`)

Four honesty checks back the budget, none of which need a gold-standard dataset:

- **Log-loss + bootstrap CI on the ECE.** The calibration receipt adds the strictly-proper log
  score (the KL cross-entropy, which punishes confident errors harder than Brier) and a seeded
  percentile bootstrap 95% interval on the ECE, so the calibration error carries its own
  finite-sample uncertainty (live: ECE 0.35% with a tight bootstrap CI, log-loss ~0.19).
- **Fitted-temperature self-consistency.** Fitting the Boltzmann temperature `T` so the softmax
  `sigmoid(m/T)` best reproduces the Gaussian posterior recovers the closed-form `T = sigma/1.7`
  exactly (Guo et al. 2017 temperature scaling), a clean self-consistency check.
- **Student-t heavy-tail sensitivity.** Re-running `P(offside)` with a Student-t(5) noise model
  scaled to the same sigma shifts the probability by under 2 percentage points even on the
  knife-edge call, so the Gaussian maximum-entropy choice is robust here, and a large shift would
  be honest to surface (the report's recommended caveat). Pure Python, no scipy.
