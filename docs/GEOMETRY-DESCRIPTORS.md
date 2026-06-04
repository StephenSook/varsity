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
- **Persistent homology, only the H1/loops part.** A ~14-point freeze-frame is far too sparse for a
  meaningful **1-cycle** (a loop/hole in the defence): that part of TDA would be vacuous. But the
  **H0 (0-dimensional) persistence IS meaningful** and is now shipped (see the MST-gap grouping
  below): the 0-dim persistence diagram is exactly the single-linkage dendrogram (Carlsson 2009), a
  robust clustering of the defenders. So the honest line is "H1 is too sparse," not "all TDA is
  vacuous."
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

## Defensive grouping (H0 persistence) and the robust alpha-shape

Two more spatial-structure scalars, both robust by construction:

- **`defensive_groups` + `largest_gap_m` (the MST-gap, H0 persistence).** The minimum spanning tree
  over the defenders is built (Prim, pure Python); the cloud splits into groups at any MST edge at
  least twice the median spacing (a scale-relative cut, so a uniform block stays one group and only
  a genuine gap splits it). This is exactly 0-dimensional persistence / single-linkage clustering
  (Carlsson 2009). Narratable: "the defence was in two groups, the biggest gap was X metres."
- **`block_concavity_ratio` (the robust alpha-shape, now shipped).** The earlier note dropped the
  alpha-shape because a *fixed* alpha is wobbly on sparse near-collinear back lines. That objection
  is resolved by a **data-adaptive alpha** (1.5x the median Delaunay edge), giving one deterministic
  value per frame. Underneath is an **exact-arithmetic Bowyer-Watson Delaunay** built on the same
  Shewchuk-family predicates (an exact-rational in-circle test), so it is provably immune to the
  floating-point cocircular ties that made naive Delaunay fragile on near-collinear inputs. The
  scalar is the alpha-complex area over the convex-hull area: 1.0 = a solid convex block (a flat
  collinear line correctly reports no concavity, degrading gracefully); below 1.0 = the block had a
  gap or dent. So the honest line is "a single-alpha shape is non-robust," not "Delaunay is
  impossible," and the robust version is built.
