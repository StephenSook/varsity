# Descriptive geometry: the defensive line as a geometric object

`services/app/geometry_descriptors.py` adds narratable spatial context for a blind fan, on top
of the offside margin. It **describes** the received decision's geometry; it never redefines the
offside line (which stays the Law-11 perpendicular through the second-last opponent) or
re-adjudicates. Pure Python (`math` + `fractions`): no scipy, no sklearn, no numpy.

## What it adds (live in the `geometry_descriptors` SSE stage)

- **An exact "ahead-of-line" predicate.** `orient2d_sign` computes the sign of twice the signed
  area of a triangle in **exact rational arithmetic** (`fractions.Fraction`), so the sign is
  provably immune to floating-point cancellation for nearly-collinear inputs. That is the
  guarantee Shewchuk's adaptive-precision predicates give (J.R. Shewchuk, "Adaptive Precision
  Floating-Point Arithmetic and Fast Robust Geometric Predicates," *Discrete & Computational
  Geometry* 18(3):305-363, 1997), the same primitive d3-delaunay and CGAL rely on. **Honesty:**
  it certifies the sign the geometry *intends*, not an IFAB verdict. It does not turn VARSITY
  into a referee.
- **The defensive line's tilt** (`tilt_deg`), fitted robustly with the **Theil-Sen** estimator
  (the median of pairwise slopes), which has a ~29.3% breakdown point, so one out-of-position
  defender does not swing it. A flat line reads ~0 degrees.
- **The line's thickness** (`thickness_m`), the spread perpendicular to its principal axis, from
  a closed-form 2D PCA (the minor eigenvalue of the position covariance, computed by hand, no
  numpy). A new narratable scalar: how tight or stretched the defensive shape was.
- **The line's lateral width** (`lateral_width_m`), the defenders' spread across the pitch.

These give a blind fan dimensions current offside coverage never speaks: the tilt of the line,
how deep the block was, how wide it stretched.

## Considered and rejected (the honest exclusion)

These were evaluated and deliberately left out, because they need data VARSITY does not have, and
saying so is itself the point (it shows where the cliff is):

- **Voronoi / pitch-control space.** Dramatic, but the standard Voronoi diagram is only correct
  in the vanishing-speed case (Efthimiou 2021) and the clipped "space behind the line" needs
  scipy + shapely. The lateral-width + thickness scalars carry the narratable value without the
  dependency, so plain descriptors win here.
- **Persistent homology / TDA.** A ~14-point freeze-frame is far too sparse for a meaningful
  persistence diagram; applying it would be mathematically vacuous.
- **Tropical / information / Morse geometry, configuration-space analysis.** Each needs
  trajectories, velocities, or populations of frames, not a single instant. Including them would
  inflate the maths footprint dishonestly.

Excluding these on principle is a Technical-Execution signal, not a gap.
