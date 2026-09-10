# Source wet shared-pressure interface review

Scope: read-only preparation at baseline fe9d684, followed by separate approval of the frozen pure rational-interval extraction. No provider construction, EOS call, model evolution, installation, or numerical-test rerun. The wet implementation and transition wiring were not yet frozen when this note was written.

## Reuse boundary

Use rational_intervals.interval_difference, interval_sum, interval_divide_positive and residual_to_root_bound for exact signed arithmetic only. Their old paired_pressure call sites retain complete legacy certificates and input bytes; KERNEL_REVIEW.md records the bounded approval.

Do not instantiate PressureState/SharedVolumes with fictional solid_mol, bulk geometry or Jacobian fields. paired_pressure_host.prepare_paired_pressure assumes the older mechanical/solid/mol host and a B-only pivot, and its observer-before-counter order loses the apparent return count when the observer throws. It is a reference for outward rounding and density-to-molar-volume conversion, not a source adapter.

SourceInversePressure already binds the complete saved state, inverse, source model, fixed dry mass, original volume/envelope and policy. Its continuation.check path is passive; it does not evaluate EOS. New shared wet declarations must bind both the actual storage and actual volume object by identity, as SourceSharedDryVolume does for its separate dry contract. Equal material digests do not establish a shared spatial parameter. The dry theorem that U(T) is independent of V is inapplicable to wet storage.

## Four-point support and observations

The physics CONTRACT.md defines common J as the outward binary64 hull of the two complete original reported-temperature pressure boxes. Both D and the full-J machine error Γ use this same support. Preflight J against the intersection of both original source/mechanical/water/envelope domains. Do not silently clip it, change uncertainties, or retry with a more convenient interval.

Plan (TA,Jlo), (TA,Jhi), (TB,Jlo), (TB,Jhi), all liquid, before the first provider call. Up to four unique state_tp requests are needed per pair. Deduplicate only exact binary64 T/P/phase under the same actual provider object and unchanged full provider binding. Never use isclose or rounded display strings. A cache shared across pairs must retain the original actual attempt index and must not confer common-volume identity across cells. Native state_tp requests may themselves contain multiple internal kernel operations, so request counts are not EOS-update counts.

Reuse the live storage.water; reconstruction can incur genuine HEOS reference-anchor work. Each returned WaterState is a full passive value with T/P, phase, density, native caloric/entropy values, residuals, reference and implementation. Preserve all fields immediately upon return. Bind source_asset_sha256 from the actual provider separately because it is not a WaterState field. Check the exact requested T/P, liquid phase, positive finite density and mass, original reference/implementation and unchanged provider identity. Molar volume is m/rho with mass in kg/mol and density in kg/m3; any extra representation conversion needs its explicit allowance.

Separate planned, attempted, returned and validated counts. Append the request before calling state_tp; retain the full returned WaterState before validation or observers. On a later failure retain every earlier return plus the failing request and exception. Run cancellation checks before each unique request, not merely once per pair. check()/compare() consume stored evidence and perform no new state_tp calls.

## Numerical and integration contract

Follow the full physics contract: positive lower/upper root signs for both endpoints and the whole original V interval; full-J stable vP assumption; strictly positive gas compliance; signed interval D; full-J normal-range arithmetic bounds Γ; ζ from this actual saved closure residual; actual fluid pressure error and total-bound projection; new thermal continuation from r0=max(old eP, distances to J), with max(old L,new L). Failure to prove a condition gives unresolved/rejection, not a narrower guessed bound. |uP| is not a bound on |vP|, and four observations do not establish global liquid stability.

The new joint result alone selects the new strategy. Preserve original independent pressure values and failure flags verbatim; do not minimize bounds with mismatched error targets. Strictly revalidate original pressure-error decomposition for this new entrance, while leaving old unilateral records usable if they do not qualify for the new one. Full input temperature and volume uncertainties remain unchanged. Material/source/event-direction qualifications do not upgrade.

SourceDryTransition can carry a 2-by-N optional wet-pair grid beside its existing dry pair. Bind each populated entry to the actual corresponding pair of cell_pressure_endpoints, time row and original live storage. Default empty strategy must reproduce the old comparison. Existing clock, N/U/T, per-cell and global path balances keep their original thresholds. One unresolved or failed wet cell still blocks aggregate acceptance. Partial collection failures must retain completed candidates and every completed wet pair/request.

## Historical cost preview only

HISTORICAL_QUERY_SHAPE.json reads the unchanged prior native N3 JSON as plain JSON. All four old wet pairs have TA=TB=325 K, so there are two numerical request keys per pair and four across the repeated event/common rows. These are not new physical observations, live-restoration evidence, root-sign checks or a promise that a future actual run passes.

Prospective finite counterexamples are listed in REVIEW_CASES.json. None were executed in this preparation.
