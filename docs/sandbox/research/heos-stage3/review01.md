# HEOS stage 3 — independent attempt01 code/result review

**BLOCK numerical/provider admission; retain this as a failed isolated experiment.** No EOS/test was rerun by the reviewer. The candidate is not registered as WaterProperties, and production remains outside this experiment. Reviewed PLAN, candidate, child, expected manifest and saved process/result files.

## Actual failure and likely mechanism

57 declared run-input hashes match current files and saved after hashes. Supervisor status is failed/child exit 1 after 1.186390457995003 s, leader reaped, no signaling error, inputs unchanged. result01.json contains no completed comparison rows: saturation validation failed before frozen-Python comparisons and domain assertions. The successful constructor anchor check does not imply the rest passed.

The seven saved residuals map unambiguously to the code. The pressure residual 7.012613423285075e-8 Pa passes; the h-u-p/rho residual **2.74099875241518e-6 J/kg fails the original 1e-6 J/kg gate**. The other five values in that tuple pass their unchanged local gates. Pair-level pressure/order/Gibbs and the planned TP comparison sequence are not established by this failure record.

There is a plausible pressure-coordinate explanation: `7.012613423285075e-8 / 2.74099875241518e-6 = 0.025584154013590998 kg/m3`, consistent with a dilute water-vapor density scale at 300 K. If native h/u use the Helmholtz density pressure while QT supplies a slightly different saturation pressure, division by this small density amplifies a tiny pressure discrepancy into the failed specific-energy identity. Thus passing the separate .01 Pa pressure gate cannot cover the stricter energy identity. This supports, but **does not prove**, the proposed superancillary/density-pressure mismatch. The failure lacks saved rho, native h/u, reconstructed pressure and quality, so those operands cannot be checked independently offline.

Keep all original gates. A next separately authorized diagnostic should save raw p/rho/h/u/T/Q and independent EOS p and test whether h-u matches that EOS pressure divided by rho. Do not overwrite p with reconstructed p, define u=h-p/rho, relax the tolerance or omit the vapor branch to erase the failure. A legitimate repair must compute a sufficiently accurate saturated state: for example, use the original estimate only as an initial guess for actual fixed-T equal-pressure/equal-Gibbs coexistence, or use a verified native accurate saturation path with an explicit configuration identity. Both phase ordering/stability and all original thermodynamic gates must still pass. This review neither selects nor executes a new solver/configuration experiment.

## Code assessment

Positive aspects: separate instance-owned flash/check AbstractState objects, RLock around whole TP/saturation transactions, immutable returned Snapshot dataclasses, mass-native properties, exact public M/R retained from source-verified original WaterReference, no fallback/reference reset, and independent Table-3 assembly from derivatives. The flash chooses phase automatically; phase imposition is confined to checking the returned density. Admission domain and original tolerances are retained. The failure is propagated rather than normalized into success.

Outstanding implementation/admission blockers are explicit:

- **Scientific identity is not frozen/revalidated.** HEOSCandidate is a mutable class; reference, _r, _mass, native objects, descriptor_json and identity can be reassigned without detecting an identity mismatch. Returned snapshots freeze their fields but cannot prove the adapter still implements their stored descriptor. A future registered provider needs immutable scientific binding and validated runtime ownership/mutation handling.
- **Descriptor omits effective config and adapter/check-policy code identity.** Package/fluid hashes do not exclude global reference/config mutation. Only a native ideal h anchor is checked; an entropy-only offset need not fail that check. This is consistent with the declared unfinished research scope, not sufficient production identity. Add the source/config/reference protections from the earlier identity audit before external admission.
- **Loaded-code verification is incomplete.** __init__ imports CoolProp before checking hashes, and the manifest hashes paths under CoolProp.__file__ without explicitly binding CP.__file__, AbstractState's provider and the loaded constants/State wrappers. The manifest itself is a caller-provided trust input. For the current frozen supervised run the evidence pins it, but it is not a generic self-authenticating backend factory. Missing/malformed source files also do not uniformly become WaterSourceError yet.
- **Reference descriptor uses repr and no policy schema.** Prefer explicit canonical fields and a versioned numerical/implementation policy. The snapshot's h/u/s are native values, whereas self.reference also includes the common formation-energy convention. This is acceptable only with clearly labelled standalone output; it must not be passed off as the existing WaterState public caloric interface without the explicit conversion.
- **Failure diagnostic/coverage is partial.** Child builds all comparison objects before appending rows and _snapshot raises before persisting native operands. Consequently one failure drops already computed partial evidence. Preserve per-stage operands in later unique attempts, including the old comparison source binding, instead of implying all planned checks ran.

These are not requests to weaken or disable checks to obtain a green stage. The current failure correctly blocks admission. Broader phase/domain/reference-mutation/fault/concurrency/consumer tests and actual performance remain unverified.

## Frozen snapshot hashes

- heos_candidate.py: `fbe88170b2c11b55a2926a62112876df04775eba58131684892c6b09ed98147d`
- child.py: `6bedb30cb6b450662a9c53237a82178960692c499b8654d86b4f71231bd6f5f8`
- PLAN.md: `b9339c9b07ff6bf934d9f94cd76dd2548ea3558ac27ec075de6c43d30fadf828`
- expected.json: `ea2d387583d8064a86d0975092737608d99648474c17ea71ee555c30bdbe3669`
- result01.json: `cbd9d34bb61a6b8fcc3479a0c05a4df24b3a60c051511eea2308d31fe0686d16`

Only this report was written by the reviewer. The numerical cause remains a hypothesis until an actual bounded diagnostic retains the required operands.
