# The uncertainty budget: GUM, Bayesian, and information-theoretic

VARSITY reports an offside margin. That number is an estimate from coarse data, so the
honest thing is to say *how* coarse, the way international metrology does. `services/app/gum.py`
is the rigorous superset of the "VARSITY's Call" band (`uncertainty.py`): a GUM-compliant
uncertainty budget, a Bayesian credible interval, the Shannon entropy of the call in bits,
and a Monte-Carlo cross-check. It **describes** the precision of the received decision's
geometry; it never adjudicates.

## The honest two-regime picture

Our coordinates are a single **broadcast-annotated** `(x, y)` per player from StatsBomb 360 , 
not limb-level optical tracking. So there are two regimes, and we report both:

- **Optical-equivalent (optimistic):** if this were TRACAB-grade optical tracking (~9 cm per
  player, Linke et al., *PLOS ONE* 2020), the margin would be good to ~13 cm. That is the band
  `uncertainty.py` reports, and the calibration receipt (`/calibration`) validates.
- **Broadcast-annotation (honest):** on the single annotated point we actually have, the
  Type-B coordinate uncertainty is far larger. The same-frame homography systematic error
  largely **cancels** in the differential margin, but the residual plus the body-anchor shape
  uncertainty give an honest expanded uncertainty of ~1 m at 95% coverage.

VARSITY leads with the honest regime. The point of the report (the Innovation angle) is that
**our coarse data correctly refuses to pretend to centimetre precision.**

## The GUM budget (BIPM JCGM 100:2008)

The margin is `m = x_attacker − x_defender`. Its combined standard uncertainty follows the GUM
law of propagation for a **difference** (Eq. 16 with sensitivity coefficients +1, −1):

```
u_c²(m) = u_a² + u_d² − 2·r·u_a·u_d
```

The **minus** sign is correct for a subtraction: positive correlation `r` (shared common-mode
homography error) *reduces* the combined uncertainty, because that error cancels. The
body-anchor shape uncertainty (IFAB Law 11 measures the furthest-forward body part, not the
annotated point) adds in quadrature. The **expanded uncertainty** is `U = k·u_c` with coverage
factor `k = 2`, which gives **approximately 95%** coverage *for an approximately-normal
distribution with large effective degrees of freedom* (GUM clause 6.3.3; the exact
asymptotic-normal value is 95.45%). The **coverage interval** is `m ± U`.

The documented Type-B inputs (in `gum.py`):

| Input | Value | Basis |
|---|---|---|
| `U_COORD_BROADCAST_M` | 0.60 m per coordinate | broadcast-CV tracking RMSE (Cranga et al. 2025, 1.68–16.39 m across providers), SciSports ("several metres off"), StatsBomb's homography article |
| `HOMOGRAPHY_CORRELATION` `r` | 0.70 | same-frame systematic error cancels in the differential |
| `U_SHAPE_M` | 0.30 m | IFAB Law 11 furthest-forward part vs the annotated point |
| `K_COVERAGE` `k` | 2 | ~95% coverage (normal, large DoF) |

These are **documented, defensible estimates, not a published StatsBomb accuracy spec, which
does not exist.** The correlation `r` is reasoned (same-frame cancellation), not measured. We
say so plainly; that honesty is part of the metrology, not a hedge against it.

## Bayesian posterior + credible interval

Under the maximum-entropy Gaussian noise model (below), the posterior on the margin is Gaussian,
so `P(offside | data) = Φ(m / σ_m)` is a one-line, closed-form computation (no MCMC), and the
95% **credible interval** is `m ± 1.96·σ_m`. This admits the probabilistic statement a frequentist
interval cannot: "there is 95% posterior probability the true margin lies in this interval."

## Shannon entropy → narration verbosity

The Shannon binary entropy `H₂(p) = −p·log₂p − (1−p)·log₂(1−p)` in **bits** is the honest measure
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
  **straddles zero** (`[−1.09, +1.13] m`), honestly too close to call, with ~1.0 bit of entropy;
  the clear scenarios stay clear with ~0 bits.
- It is **not** field calibration against limb-tracked ground truth (StatsBomb 360 has none), and
  the Type-B budget is a documented estimate, not a measured spec.
- It **describes** the received decision's geometric precision. It never re-adjudicates the call.
