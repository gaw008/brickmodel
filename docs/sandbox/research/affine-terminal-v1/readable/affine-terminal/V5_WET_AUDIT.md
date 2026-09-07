# V5 independent wet audit

## Run 0 actual completed evidence

Independently audited saved result, callback and source metadata with exact Fraction arithmetic and file hashing only. No EOS/tests/imports, script edits or second trajectory execution. Detailed per-prefix values are retained in v5-wet-audit.json.

Result SHA256 deb3bb48ea020116370faadbd2b9796c51c9a8b9c48d2ad14604edf67f369b59. Supervisor complete/child 0, 89.42923720799445 s; inner completed 87.84569445899979 s. All 182 input hashes match before/after/current bytes. All loaded module records before/after match current installed and source bytes. Fresh callback passed and its full initial state matches the trajectory initial state.

Recomputed all 14 accepted prefixes including the event correction exactly. Each cumulative species/energy Fraction and accumulated absolute component residual equals the stored total. All five work components plus exact sum residual equal total work at every step; closed face fluxes and body work are zero. No extra mechanical-composition power term is introduced. Maximum C residual is 1.7997756063259374e-16 mol, H 4.698385879301197e-22 mol, O 2.3491929396505986e-22 mol, accounted solid+water mass 2.159728641327866e-18 kg, energy prefix 5.117078364090836e-11 J, each-species ledger 1.7997734887435692e-16 mol and analytic A 8.894662784086904e-12 mol. All original gates pass. Carrier and energy identity are preserved; no unsupported elemental composition is assigned to carrier.

Event at 0.5002854010435919 s uses a certified affine endpoint. Independently reconstructed each integrated face-species/face-energy/reaction/work field and each component quadrature from the two saved observations. Every stored field and declared quadrature rounding matches. The exact inventory polynomial is decreasing; endpoint residual 3.0372732431419886e-19 mol is nonnegative and the immediate next float is negative. Recorded root-time bound 1.1102230246251565e-16 s crosses the polynomial root and meets the original budget. This certifies the sampled polynomial endpoint, not the true nonlinear ODE root.

Actual liquid correction is 3.037274860396709e-19 mol, vapor storage roundoff -6.617444900424221e-23 mol. Reconstructed panel remainder, opposite ideal transfer, actual vapor increment, half-neighbor limit, local ULP budget and all original absolute/fraction/storage/element/mass limits pass. Positive gross affine evaporation is independently integrated and stored downward, so it cannot loosen its fraction budget. Correction totals and all post-event species prefixes include actual vapor storage roundoff; energy is unchanged by writeback.

Two terminal comparisons and the independent halved-controls approach passed. Stored aggregate event metrics are time 4.205302772675168e-12 s, N 8.411049634560186e-13 mol, E 5.820766091346741e-11 J, T 8.278101959788744e-8 K and P 0.004807914764697182 Pa, all within original gates. Actual 260 evaluations and 31 trial panels exactly match phase sums, with 6 reused observations/4 reused panels separately recorded. End time is 0.5078125 s; dry mode retains zero liquid, nonzero transfer coefficient 1e-6 and positive A-to-B reaction (final extent 0.19984381102015425 mol/s). Final T/P are 299.99779652733434 K / 54952.591565962415 Pa.

Run 0 is a passing source-qualified-water/manufactured-solid integration case. Cross-cap convergence remains pending second terminal evidence and comparison. This is not raw-sludge/free-sintering validation or an independent wet temperature oracle.


## Run 1 and completed two-cap comparison

Second result SHA256 636e25291e4c6bf65c78fa661ecebea56fca89bf0fb02a7eb0c98b6c12e95182. Supervisor complete/child 0, 87.09586816700175 s; inner completed 85.50177658299799 s. All 182 input hashes match before/after/current and each before/after loaded module matches installed/current source bytes. Recomputed all 16 accepted prefixes, complete correction-aware species/energy totals, component sums and all terminal affine fields and quadrature roundings. The same certified endpoint, gross-evaporation downward bound, local ULP/half-neighbor and absolute/cumulative correction/element/mass budgets pass. Maximum C residual 1.3198128570937606e-16 mol, H 4.698385879301197e-22 mol, O 2.3491929396505986e-22 mol, accounted mass 1.5837711963784736e-18 kg, E prefix 5.117078364090836e-11 J and analytic A error 2.2368773500147654e-12 mol. Actual 303 evaluations/36 trial panels match phase accounting; reuse remains separately recorded.

Independently recomputed all comparison-result.json values and verified both referenced result hashes and byte lengths. Initial states match exactly. Original comparison gates all pass:

| Difference | Actual | Original limit |
|---|---:|---:|
| Endpoint amount | 6.6579933840488215e-12 mol | 1e-10 mol |
| Endpoint energy | 2.6106135919690132e-8 J | 1e-6 J |
| Endpoint temperature | 2.604963356134249e-9 K | 1e-5 K |
| Endpoint pressure | 3.9664882933720946e-7 Pa | 1 Pa |
| Event time | 0 s | 1e-7 s |

Important numerical scope: both runs have the exact same accepted wet states, ledgers and times through the event. The outer maximum step cap is inactive for that inventory-limited wet prefix; halving it changes actual dry continuation, yielding 14 versus 16 accepted total steps. Zero event-time difference across these two caps is therefore not an independent event-time convergence/order measurement. Each run separately retains genuinely different original/halved-controls wet approach grids and passes its independent local event/common-time comparison under the unchanged gates. This is useful local wet evidence and dry continuation cap sensitivity, with no claimed global convergence order or independent wet temperature oracle.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: both bounded manufactured reacting/wet runs and their prescribed comparison pass independently audited accounting, clock/correction and provenance checks. Retain the inactive wet-cap limitation. This does not establish source-qualified raw sludge, free sintering, full model completion or the separately running installed full-suite result.
