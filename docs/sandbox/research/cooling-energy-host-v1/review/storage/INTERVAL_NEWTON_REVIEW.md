# Limited scalar interval-Newton review

Status: **APPROVE the limited scalar performance increment**. No unresolved mathematical or numerical-certificate issue was found in the reviewed diff. The previously approved storage baseline remains SHA256 `68d3f6b222b01a05c28c583f2575cfe46ca4d923eeb6729fd79c1411f34714cd`.

The final implementation reviewed is SHA256 `d98d6dccff4e31895da642ffa170ecd208c60e6e55b27ac5e314c36ace3f4579`; its author tests are SHA256 `31ec6280dc1d97c648bddea9b508b651f2e6d439f2dc8b518ad814dc2d66e4fc`. The diff adds only `_interval_newton` and its use in scalar interval updates. Existing feasibility/existence checks, target/temperature policies, final public residual certificates, and plate evaluation remain intact. The archived baseline source was verified against its original SHA.

For the existing exact feasible interval I=[q_lo,q_hi], all component inverses satisfy T_i(q) in [T_lo,T_hi], with h(T)=CT-bT², Ce=C-2bT>0, and q≥T_lo²>0. Thus F(q)=mean(h⁻¹(x_i-bq))-sqrt(q) has derivative

`D(q)=-F'(q)=b mean(1/Ce_i(q))+1/(2 sqrt(q)) > 0`.

Valid rational derivative bounds are

`L=b/(C-2b T_lo)+1/(2 sqrt_upper(q_hi))`

`H=b/(C-2b T_hi)+1/(2 max(T_lo,sqrt_lower(q_lo)))`.

The max in H is necessary because an absolute-precision square-root enclosure can have a zero lower endpoint for positive subnormal-scale temperatures. T_lo remains an exact positive bound and avoids dividing by zero without leaving the declared domain.

If r is the existing certified root and m lies in I, the mean value theorem gives F(m)=D(xi)(r-m), for xi between r and m. An outward interval [f_lo,f_hi] enclosing F(m) therefore implies

`r ∈ m + [f_lo,f_hi]/[L,H]`.

General interval division must use the minimum and maximum of all four endpoint quotients, because the F enclosure may contain zero or have either sign. Intersect this interval with the original certified I. A strict subinterval remains certified to contain the same root; neither the target energies nor the component-feasible domain are changed. An empty intersection contradicts the numerical certificate and must be a resolution failure, not newly alleged physical nonexistence. No useful contraction must retain the original bisection fallback.

The original exact feasible-domain construction, scalar endpoint existence proof, final actual binary64-T residual assessment, target-error admission, positive reported heat-capacity lower bound, and original precision/tolerance policies remain acceptance requirements. Acceleration alone changes none of those.

Final measurement is limited to the three pre-existing B points supplied by root, with target errors zero and policy `(1e-10 J, 1e-9 K, 200 iterations, 160 sqrt bits)`. Only one inverse per point is timed after construction/forward; no performance scan, time integration, or gate relaxation is authorized in this review.

## Final independent evidence

- **91 passed in 0.14 seconds**: author 63 storage tests, previous independent 20 storage tests, and 8 new independent interval tests. The existing installed Python ran pytest with bytecode/cache disabled. Host tests were not included.
- The added independent tests derive exact energies and the exact root q from original B coefficients at uniform lower/upper domain endpoints, a lower/upper mixed endpoint, and a nonuniform interior state. They verify root retention inside the original component-feasible interval with 8-bit and 160-bit outward square-root precision, including collapsed feasible intervals.
- Reviewed author tests additionally exercise both signs of F, a sign interval crossing zero, an underresolved zero square-root lower endpoint, contradictory bounds classified as numerical resolution failure, and the no-contraction fallback whose successive widths are exactly halved.
- Implementation uses all four signed endpoint quotients, the positive exact temperature-domain bound, and exact dyadic floor/ceiling before intersecting the old interval. The dyadic enclosure prevents denominator growth while preserving root inclusion. A separately proved sign half-interval can only strengthen that inclusion.
- Each of the three timed decodes was followed by an independent Fraction recomputation at its actual returned binary64 temperatures. Public residual bounds and `norm(residual)^2 <= (returned_radius * returned_dmin)^2` passed under the unchanged policy and zero target-error vector.

| Existing B point index | Root's archived baseline: iterations / ms | This review: iterations / ms |
| --- | --- | --- |
| 0 | 35 / 4.110 | 4 / 0.974 |
| 50 | 35 / 4.504 | 4 / 1.018 |
| 100 | 36 / 4.612 | 4 / 1.382 |

Detailed independent measurements are in `three_point_interval_newton_review.json`. Baseline timings and original trajectory provenance are copied from root's frozen three-point evidence, not remeasured here. The current timings are single samples per point and do not certify full-trajectory wall time. The original step sizes, numerical thresholds, and 130-second gate remain unchanged. No integration or host audit occurred.
