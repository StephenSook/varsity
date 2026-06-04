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

## Spatial-structure scalars (the convex hull + free space, the Voronoi-lite delivered)

The Voronoi "space behind the line" the report wanted is now delivered without scipy/shapely:

- **The defenders' convex hull** (Andrew's monotone chain) + its **footprint area** (shoelace),
  the report's named structure, pure Python.
- **`free_space_behind_line_m2`** is a seeded Monte-Carlo estimate of the area behind the offside
  line that no defender could reach first (farther than a defender's reach from every opponent).
  This is exactly the vanishing-speed case where the standard Voronoi diagram is correct
  (Efthimiou 2021), so a simple sampling estimate carries the narratable "X square metres of space
  behind the line" scalar without the dependency.
- **`line_step_m`** captures the report's "the right-back was 4 m deeper" descriptor as the
  x-spread of the three deepest defenders, robustly and without a triangulation.

**The alpha-shape concave hull is honestly dropped, and the reason is a real one, not effort:**
the canonical alpha-shape is Delaunay-based, and a Delaunay triangulation is numerically fragile
precisely on the near-collinear point sets that dominate our data, a flat or near-flat defensive
line. A robust implementation would need exact-arithmetic Delaunay for a descriptor whose value
(the concave outline of all visible opponents) is marginal over the convex hull + thickness +
stepped-line already shipped. The free-space scalar carries the spatial-control narration instead.
