# Affine terminal localization review

Read-only against current source, 2026-09-08. No native EOS or production changes. Scope follows docs/sandbox/research/thermal-timescale-v1/NEXT_GROUP_PLAN.md.

**Conclusion:** existing evidence certifies the represented affine surrogate's arithmetic, root rounding, polynomial positivity and numerical cross-refinement consistency. It does **not** bound the actual coupled liquid RHS remainder, so it cannot currently provide rigorous true per-member event-root intervals for a group. This limits the new proposed true-root group contract; it does not retrospectively relabel existing single-event numerical acceptance as a validated ODE enclosure.

## Exact code evidence

- depletion_integration.py:195–200 calls AffineTerminalEvidence “actual two rate samples and midpoint predictor.” There is no remainder/error-envelope field.
- affine_terminal at562–606 constructs an Euler predictor for the represented midpoint from the initial rates, including N/E/mechanics, then calls the actual operator at that predictor. Thus the second sample is the genuine RHS **at the predictor**, not the RHS at a certified true midpoint state.
- Lines575–583 integrate every field as h*r0+h²*(rm−r0)/(2*hm). Lines610–615 give that same two-sample polynomial to locate_affine_depletion_clock. There is no bound for interpolation curvature, initial-state error propagation or midpoint predictor error.
- Lines619–631 check the entire reconstructed inventory polynomial and its interior minimum. This proves positivity/noncompetition for that polynomial; it is not positivity of all actual ODE trajectories allowed by state/rate errors. Competing liquid zero is explicitly rejected.
- Lines634–639 integrate the positive part of the affine evaporation rate for the local correction fraction. This is carefully rounded-down surrogate quadrature, not a certified lower bound on actual physical gross evaporation in the presence of an unknown RHS remainder.
- affine_depletion_clock.py:83–86 derives exact Fraction coefficients solely from the two represented rate vectors. Lines88–109 verify each represented panel term against those exact integrals. Lines110 onward certify polynomial crossing; event_time_rounding_s at72–81 bounds the represented polynomial root/end-point gap. None of these quantities includes physical/numerical rate-model defect.
- Whole-state terminal/common comparisons in depletion_integration compare two successively refined numerical paths, plus the independent approach when enabled. These are meaningful convergence checks with original gates, but no validated remainder estimate follows merely from two paths agreeing. A common systematic error can survive both.

## Concrete missing contract

For each member i, need a justified function/envelope R_i(h) such that |N_i,true(t0+h)−q_i(h)|<=R_i(h) over the entire terminal interval, not just two observations. It must include:

1. Initial N/E/stretch state enclosure and its propagation through coupled temperature/pressure inverses, fluxes, mechanics, reaction and phase transfer.
2. Native/source rate evaluation error at the sampled states. Current reported-T pressure and inverse-T errors do not alone yield a bound on phase rate: a source-qualified sensitivity/enclosure for chemical equilibrium/partial pressure and transport over the relevant state tube is needed.
3. A defect or time/state-derivative bound between samples, including the fact that the midpoint is predicted. Local numerical derivatives or extra samples cannot simply be promoted to a domain-wide Lipschitz bound.
4. A strictly decreasing crossing bound −dN_i/dt>=m_i>0 where root localization is required. Then a valid inventory enclosure can be converted into a time enclosure (or signs of q_i±R_i can directly bound the crossing). Without slope separation, tiny inventory error can cause arbitrarily large root-time uncertainty.
5. Bounds for physical inventory/time displacement and actual gross evaporation if several unresolved roots are collapsed to one mode-switch time. Existing roundoff budgets cannot be reinterpreted as those missing errors.

No finite number of matching samples proves the missing curvature bound: add a smooth bump to the liquid RHS that vanishes at both sample times but has nonzero integral between them. The existing observations and exact affine clock remain identical while the actual root changes. Likewise predictor-state error can alter the second rate even without interpolation curvature.

## Smallest honest next integration step

Implement the proposed pure affine multi-root module for explicitly affine analytic providers and use its independent examples to distinguish exact common roots, ordered roots and unresolved unions. Name its output `affine_surrogate_root_interval` unless the provider explicitly supplies a validated remainder contract; never pass an unqualified true-root label into the group selector.

For eventual actual wet admission, add an optional immutable per-member localization-envelope interface containing domain/state tube, defect/remainder bound, crossing-slope bound, source identity and qualification. Default absent means true group localization unavailable. An initial implementation can accept only analytically justified manufactured envelopes; real wet adapter admission remains off until its coupled interval/sensitivity proof exists. Do not invent zero remainder from the existing AffineTerminalEvidence or from successful refinement.

An alternative numerical-only group method can be designed around existing refinement semantics, but must be explicitly a new numerical acceptance contract with order/mode/correction tests; it is not the stronger certified true-root grouping required by NEXT_GROUP_PLAN. This distinction must be decided openly before changing the selector.

Existing record auditor should continue to replay the current clock and field quadrature as arithmetic evidence. A future version must separately audit the new envelope's domain/input/source binding and group union/order/correction claims; a hash match is not a proof of the envelope. No ordinary/terminal source guard or original six gate should be weakened to bridge this gap.
