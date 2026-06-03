# Offside geometry: what it is, and what it is not

VARSITY's geometry engine (`services/app/geometry.py`) takes the **received** offside/VAR decision
and a StatsBomb 360 freeze-frame as inputs and produces a single, **illustrative** margin: the
x-distance from the flagged attacker to the offside reference line of Law 11. It **describes** a
decision so a blind fan can hear it. It does **not** adjudicate.

## Units: the StatsBomb grid is in yards

StatsBomb standardizes every event onto a **120 × 80 grid whose units are yards**, so a margin in
grid units converts to metres with the international yard, **1 yd = 0.9144 m**. We do **not** assume
the 120-unit length spans a 105 m pitch (the `105 / 120 = 0.875` factor): that double-applies a
normalization StatsBomb never performed and under-states every margin by ~4.3 %.

Sources:
- mplsoccer "Standardize data" docs convert StatsBomb distances with `* 0.9144  # note converted
  from yards to meters`.
- The StatsBomb Open Data Events spec measures `pass.length` in yards and defines a "switch" as a
  pass travelling more than 40 yards of the pitch width.
- The Hudl/StatsBomb live schema documents event `z` height **in yards** on the same `0-120 / 0-80`
  pitch frame as `x`/`y`.
- 1 international yard = exactly 0.9144 m.

## The Law-11 reference it encodes

- Offside position requires being in the **opponents' half** (excluding the halfway line, `x > 60`)
  **and** nearer the goal line than **both** the ball **and** the second-to-last opponent.
- The reference line is the **nearer of the second-to-last opponent and the ball**
  (`max(second_last_x, ball_x)`); the margin is signed against it, so a player ahead of the defender
  line but behind the ball reports a **negative (onside)** margin, never a misleading positive one.
- The **keeper is intentionally included** in the candidate set: the line is the second-last
  *opponent*, whoever that is (usually but not always the keeper).
- **Level is onside.** An exactly-level attacker is onside, with a tiny tolerance so float noise at
  the line never produces a self-contradicting "offside by 0.00 m". The cm-scale "too close to call"
  is surfaced honestly by the uncertainty band (the ~13 cm "VARSITY's Call"), not a hard verdict
  flip - VARSITY never overrides the official.
- The margin is the **goal-line-normal (x-axis) distance**, not a Euclidean distance (which would
  inflate it with irrelevant lateral separation).

## What VARSITY does NOT do (the precision contrast)

StatsBomb 360 gives a **single `(x, y)` point per visible player**, in 1-yard quantization, only
inside the broadcast frame, at a single instant. So this is a **coarse, point-based approximation**.
It cannot and does not reproduce:

- **FIFA Semi-Automated Offside Technology (Qatar 2022):** 12 dedicated tracking cameras following
  up to 29 body points per player at 50 Hz, plus a ball-mounted IMU at 500 Hz.
- **The Premier League's iPhone-based "Dragon" SAOT:** ~30 iPhones per stadium capturing ~10,000
  surface-mesh points per player at 100 fps, with a ~5 cm "benefit of the doubt" attacker tolerance.

When the broadcast frame does not include two defenders, the engine raises rather than inventing a
line, and the caller surfaces an indeterminate state. **Faithfulness ≠ correctness:** VARSITY's
narration is faithful to the proof and the Law; the underlying call's correctness is bounded by the
input data, and when the geometry and the official disagree, **the official's decision stands**.

## Verify

```bash
cd services
python -m pytest tests/test_geometry.py tests/test_geometry_properties.py -q
```

The property-based tests (translation invariance, scaling homogeneity, sign consistency, yard
conversion) catch the sign, half-flip, and units bugs that a single wide-margin anchor cannot.
