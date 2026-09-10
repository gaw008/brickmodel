# Pure net-inventory root reuse delta

Read-only arithmetic route against frozen115. No production edits, EOS, implementation or acceptance claims. Existing complete SourceAffinePanel construction and source bindings remain authoritative; this note adds only the first-root arithmetic route. Keep original evaporation-based correction/writeback gates unchanged.

## 1. Concrete extraction points

- `mass_wet_exact_stage.InventoryPolynomial.minimum` (line140) already evaluates an exact quadratic's endpoints/interior vertex and returns minimum plus time. Import it directly. Use its coefficient convention **n + r*t + q*t²**, not the `n+r*t+a*t²/2` convention in `exact_root_order._minimum` (line30). Conversion is q=a/2.
- `exact_affine_depletion.locate_exact_affine` (line129, midpoint/sign update at139–143) and `exact_root_order.order_exact_affine_roots` (line81, synchronized update at133–136) contain the same rational bisection transition. Extract **one pure refinement operation** accepting a validated polynomial and rational bracket `[lo,hi]`, computing `m=(lo+hi)/2`, then retaining `(m,hi)` for p(m)>=0 or `(lo,m)` otherwise. Both legacy callers use this exact operation with their existing starting interval and policy loops. Do not change iteration numbering, dyadic grids, >= tie convention, error messages, refinement limits, or when legacy ExactAffineEvidence is constructed.
- The new pure layer prepares a first-root bracket from n/r/q/H before using this shared refinement; it does not instantiate ExactAffineSamples or ExactAffineEvidence. Their evaporation/ULP/fraction budgets (`exact_affine_depletion.py:87–110`) are not root-existence conditions and must not enter the new net-fluid root record. Legacy callers retain those exact evidence constructors and gates.
- `exact_root_order._same_first_root` (line36) currently performs rational polynomial GCD and assumes both candidates are strictly decreasing. Extract its **polynomial GCD arithmetic**, preserving old `_same_first_root` wrapper behavior. A new wrapper must check that a common root belongs to each candidate's **first-root interval**, not just `(0,H]`: two nonmonotone polynomials can share a later root but have distinct first roots. Do not directly reuse the old same-first predicate on general quadratics.

Proposed minimal pure records: `QuadraticFirstRoot(polynomial, domain_duration, initial_branch_lower, initial_branch_upper, lower, upper, refinement_count, root_kind)`; root_kind is `crossing`, `exact_tangent`, or `exact_endpoint`. Exact point roots have lower==upper. A separate `QuadraticNoRoot(polynomial,H,minimum,minimum_time)` requires strictly positive minimum. Records retain original InventoryPolynomial labels and rational coefficients; no new hash framework. Construction/revalidation recomputes bracket/branch conditions from these coefficients.

## 2. First-root domain logic (all exact Fractions)

Require n>0, H>0, all coefficients/time explicitly Fraction, domain `[0,H]`. No coefficient epsilon or clipping. `minimum(H)>0` excludes a root. Otherwise:

1. **Linear q=0:** root exists only with r<0 and tau=−n/r in `(0,H]`; tau is exact rational. Pure layer may return point root; legacy wrappers continue their existing dyadic enclosure and correction behavior.
2. **Convex q>0:** an interior minimum at v=−r/(2q), with 0<v<=H, brackets the first root on `[0,v]`. If p(v)=0, this is an exact tangent; return a point record and mark it explicitly. If p(v)<0, bisect `[0,v]`. If v>H, the polynomial decreases throughout the domain, so use `[0,H]` only when p(H)<=0. v<=0 implies no root for n>0.
3. **Concave q<0:** any positive vertex is a maximum. When 0<v<H and p(H)<=0, use `[v,H]` (initial gain is permitted); otherwise, for a decreasing branch with p(H)<=0 use `[0,H]`. No root can be hidden in a concave polynomial with both endpoints positive. Endpoint p(H)=0 is exact and classified separately.

The bracket begins no earlier than the descending branch and is certified to contain the first zero in `(0,H]`. Refinement is purely numerical; do not infer physical disappearance from a tangent. For a convex dip then recovery, the first downward crossing is the boundary even if p(H)>0. Legacy globally decreasing ExactAffineSamples deliberately reject this shape; that restriction remains unchanged in the old wrapper.

**Zero-initial inventories:** this proposed primitive explicitly rejects n=0. An event driver cannot silently ignore a gas already at zero. It must separately establish all-domain nonnegativity/zero-state behavior or return unsupported; no such dry/zero-branch law is supplied by this extraction. Every positive-initial gas and liquid in the declared complete panel participates in competition, not only wet liquid cells.

## 3. Competing inventories and exact test cases

A source-level numerical ordering layer supplies all candidate labels `(family,cell,index)` and uses shared refinement for every overlapping enclosure. Earlier gas depletion blocks a proposed liquid event. A first group containing multiple liquids or a gas/liquid coincidence is a **tie result**, not a cell-index choice or event authorization. Tangency is reported even if the path merely touches zero and recovers. Strict interval separation establishes order; when two intervals touch, refine or use exact GCD/point membership. Exhaustion returns unresolved with brackets. A root at H counts in the closed numerical domain; a root just beyond H does not.

Fixed exact tests before any physical-driver integration:

| Polynomial / pair, H | Expected pure result |
|---|---|
| n=1,r=−2,q=0,H=1; phase=0 with net drainage | exact crossing tau=1/2, no evaporation prerequisite |
| net r=−3/4 from drain1 plus condensation1/4, n=1/2,H=1 | crossing2/3; never relabel drain as evaporation |
| 1+t−2t²,H=1 | initial gain then endpoint root1 |
| 1−4t+4t²,H=1 | exact tangent1/2; no disappearance inference |
| 3−8t+4t²,H=2 | first root1/2 despite final inventory3>0; second root3/2 ignored |
| 1−t+t²,H=2 | strict exclusion; minimum3/4 at1/2 |
| gas1−4t vs liquid1−2t,H=1 | gas root1/4 precedes liquid1/2 |
| two liquid polynomials1−2t and2−4t,H=1 | exact simultaneous root1/2, no index tie-break |
| (t−1/4)(t−3/4) vs (t−1/2)(t−3/4),H=1 | distinct first roots1/4 and1/2 despite common later root3/4 |
| any case shifted by exact origin2^80+1/3 | same elapsed roots, preserved exact absolute times |
| n=0 or float coefficients; H<=0 | explicit unsupported/invalid input |

Legacy regression must assert identical old locate/order return records and failures on their original decreasing inputs, including refinement count and original evaporation correction budgets. New tests should include forged root/no-root records, a one-ulp-separated represented-coefficient pair, and exhausted refinement without invented ordering. This pure extraction enables net liquid/gas numerical root evidence; it does not establish a valid physical stage, correction permission, dry mobility, rewetting, or event commit.
