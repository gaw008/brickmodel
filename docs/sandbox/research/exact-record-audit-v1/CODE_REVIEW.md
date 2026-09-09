# Independent partial exact-record audit review

APPROVE source fb8e9a235592ad3e225fab538cb3425fdf9d6af5acf0bed30056fe786bc057a6 and test ca0ff0bafa19316b885d4878cb60adfefae70ae325c5d6f05b947e894a3d8133 for the expressly partial audit contract. No blocking findings.

The entrypoint consumes the fresh validate_binding return, compares the complete original initial state, exact interval and original policies against external arguments, verifies energy and water-mass identities, and repeats live source binding after arithmetic. Caller-replaced record projections do not become trusted. Policy tolerances and original cumulative totals are not reset at event boundaries.

Every accepted step and original-initial prefix uses exact Fraction arithmetic on represented shared-face fluxes, reaction sources and work. Selected correction increments enter liquid/vapor once, including actual vapor-storage rounding. Energy is unchanged by phase writeback. Component sum residuals are independently recomputed from represented component values and their cumulative absolute magnitude is bounded. Mechanical local and cumulative represented increments, increments minus recorded exact-quadrature roundoff, and cumulative absolute quadrature error all retain the original stretch tolerance.

Each committed selected terminal rebuilds ExactAffineSamples and ExactAffineEvidence under the original roundoff/time policy, checks its saved mode-specific source identity, initial/midpoint signed liquid rates and separate positive evaporation samples, and binds panel start/end and represented liquid terms. Existing pure evidence constructors revalidate the adjacent dyadic enclosure and original correction bounds. exact_depletion_writeback recomputes the entire corrected state, correction record and cumulative totals, including zero-correction handling. Full state equality prevents an unrelated component being changed during writeback.

This is arithmetic over saved observations, not independent reproduction of the physical callback. In particular, verifying a selected polynomial does not establish earliest root among all candidates; recorded stretch quadrature diagnostics are budgeted but not rederived from all stages. These omissions, all six-gate/refinement checks and discarded resource history are accurately listed in missing_gates. PartialExactAudit is immutable and always resume_authorized=false. No continuation entrypoint is exposed. The approved scope must remain attached when reporting successful results.

Independent pure test rerun: 7 passed in 11.47 s. Tests include actual nonzero manufactured corrections and cumulative-phase tampering, final N/E/stretch corruption that passed structural decoding, changed original policy, cancelled-prefix audit and replaced caller fields. Preserved earlier failures distinguish the structural-only gap and an initially exact-zero correction fixture. No EOS, installation or repository edits occurred during review.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — original-prefix and selected-writeback arithmetic only; not complete acceptance or resume authority.
