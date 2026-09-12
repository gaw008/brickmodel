# Unique source-conductivity native01

Register before execution. Base commit 3683a6f; source/installed files must first
pass final independent code review and be frozen and installed identically.
No physical run has yet been attempted for this branch. Reuse the same two-cell
case from the completed sorption phase, replacing its static .5/.7 W/(m K)
conductivities with zero static contribution and explicit Septien donor k(W).
All geometry, gas transport, local phase, water backend, pressure/temperature
inverse policies and initial states retain their prior values. Provider source
and model/approximation files plus actual original XML join supervisor inputs.

Previous actual two-cell operator cost 3.428046 s and six-call segment cost
19.983667 s support this same two-step .05 s segment, with small read-only
conductivity lookup arithmetic added. Keep original 60 s integrator, 80 s driver,
100 s supervisor and 5 s cleanup; do not first repeat the old cost probe. One new
numbered native attempt; preserve returned prefix/run or failure unchanged.

Retain prior 1e-5 J/1e-6 K inverse, 1e-8 J/1e-12 mol cumulative arithmetic limits,
original two-step/six-call clock, shared face/phase conservation, positivity and
T/W/P gates. Require each cell's final temperature change exceed its final
inverse bound plus 1e-6 K, as before. This is a short active-coupling check, not
a convergence or complete drying claim.

Additionally retain the **actual midpoint** source-conductivity witness on each
accepted face integral. Independently calculate k from printed nodes
(23/77,.056) and (47/53,.062) using the midpoint's represented W. Check nominal
Fraction and projected k, actual Q integral, positive nominal thermal entropy,
source IDs and false material flags. Require midpoint k differs from accepted
endpoint k and final k differs from initial k: no initial-k freezing. Save
INITIAL/provenance and full returned RUN before acceptance checks.
Independently recompute Fraction R/G/exact Q, projected G, actual Q in the shared
kernel's stated floating-point operation order, its saved arithmetic residual,
and the numerical value of Q*(1/TR-1/TL); positivity alone is insufficient.

The witness contains G, Q and an explicit conduction arithmetic residual. G is
computed from exact represented k/geometry and projected for presentation;
actual Q retains the original shared face kernel's operation order. The saved
residual is not a physical model-error bound. Other gas/phase coefficients remain
manufactured and must not inherit the conductivity source qualification.

The Septien donor is VIP faecal sludge, different from Arlabosse material.
Measurement temperature is unknown; constant k at fixed W across 35–95°C and
cross-material application remain declared assumptions. No confidence interval
for the transferred/interpolated k is invented. Only W=.30–.80 is permitted.
