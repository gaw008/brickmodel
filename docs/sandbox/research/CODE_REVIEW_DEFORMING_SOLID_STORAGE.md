# DeformingSolidStorage independent point-storage review

Verdict: **APPROVE for the isolated point-storage candidate**, conditional on its declared numerical/geometry bounds and manufactured temperature-independent skeleton. It is not an integrated deforming host or a tagged ConservedState implementation.

Read complete candidate source/tests, README, verification history and actual nested storage/solid/skeleton identity contracts. Independently executed the final 11-test suite, including nonzero-liquid cases: **11 passed in 2.18 s**, XML `/private/tmp/deforming-solid-storage-review.xml`. No long EOS/integration or installation suite was repeated; no author source/tests were changed.

## Actual identity and state scope

Solid identity is derived from every field of the exact IncompressibleSolidPhase dataclasses and nested caloric/volume/error/source data, with float hex encoding and stable sorted mapping serialization. The skeleton's opaque declaration must equal that computed digest; arbitrary names and modified caloric/volume providers fail. A separate complete template digest covers gas/fluid/geometry/error policies and source-gated water reference, asset hashes and numerical limits, and is rechecked before evaluation. Runtime water backend/cache is intentionally excluded; this is scientific configuration binding, not protection against arbitrary in-process code substitution.

Reference geometry, skeleton cell, fixed complete solid inventory and model/error-domain identities are retained. The point module has no transport face geometry; a future host must additionally bind A/d/count and pass actual current geometry to transport. Explicit TotalEnergyTarget checks total-energy scope and model identity; a bare float or thermal-only label is rejected. This does not attach a scope to arbitrary ConservedState arrays, initialize an integrated total-energy trajectory or propagate work-component ledgers.

## Error propagation and inverse

At fixed time and fixed Ns, motion/skeleton energies are temperature independent, so removing their energies from a total target leaves exactly the existing thermal closure problem. Current bulk uses the actual motion volume. In exact Fraction arithmetic, its error includes J times reference-volume uncertainty, mismatch of template reference volume with exact A0*L/cells, current volume representation residual, and explicitly declared additional bulk error. Positive available-pore and pressure/error-domain gates remain active in ordinary SolidFluidStorage.

Elastic energy is linear in represented reference V0. The added reference-volume contribution bounds its magnitude using |Eel| plus numerical Eel error, multiplied by the reference-volume error ratio. Both skeleton energy numerical errors and the additional declared mechanical bound are included. This does not cover unknown material/strain/temperature effects automatically: additional bounds are conditional supplied contracts. Fixed intrinsic solid volume and a temperature-independent potential are essential restrictions.

Forward total energy is the exact rational sum of represented thermal, elastic and interface energies rounded once, with that addition residual included in the returned total bound. Inversion subtracts elastic/interface energies in Fraction arithmetic, then passes target uncertainty + mechanical uncertainty + subtraction rounding outward to the separately reviewed thermal inverse. Its strict endpoint, residual and capacity/radius gates retain that entire interval. TotalEnergyTarget also includes exact Fraction-to-float conversion error. Tiny nonzero values/errors unsupported at this scalar boundary fail explicitly rather than silently becoming zero; this differs intentionally from the lower-level thermal inverse's outward subnormal-bound support.

An additional independent dry check at two motion times supplied 1e-4 J target uncertainty and 2e-4 J additional mechanical uncertainty. Using the independent constant capacity C=10+.01*(30−R), both extreme temperatures 300±3e-4/C lay inside each returned inverse radius. The propagated thermal target error was at least 3e-4 J. This supplements the author's exact addition/subtraction, increased volume-error, wrong-scope/model and insufficient-precision tests.

## Actual wet evidence and preserved failure

The final suite exercised source-gated liquid water with Nliq=1 mol, unchanged manufactured solid/gas composition, current volume compression and full total-energy inversion. Pressure separation exceeds the sum of the **fixed-temperature** pressure bounds; the actual thermal inverse bracket/radius includes 300 K under the unchanged 1e-6 J / 1e-6 K policy. This is point compression/closure, not phase-transfer dynamics or trajectory accuracy.

The first wet test correctly failed the original precision gate with the original broader solid-volume uncertainty; that failure and test snapshot remain archived. The succeeding fixture separately defines constant v=Fraction(1,50000) m³/mol and uses its own numerical error/source identity. Independently checked the representation difference `Fraction(2e-5)−1/50000 = 1509/922337203685477580800000`, which is below one ULP. This is a new exact manufactured definition, not improved experimental knowledge or reduced uncertainty for the old material. The original broad-uncertainty failure is retained as a regression, and its energy bound was not silently narrowed.

Independently verified all **9** verification-manifest file hashes, including source/tests, README, preregistration, initial missing-module RED, wet-failure archive/output and full fixture audit. No source-backed real material parameter was qualified by these tests.

## Final isolated bindings

- `deforming_solid_storage.py`: `a4a484ef28380bd31d2eed607b5dfcdf9a5f97182c00f8a41b13d8917f91d3ef`.
- `test_deforming_solid_storage.py`: `74b3cf30e455c0300a71e4c5bd47ce17b2482ff36a68c15c06d2c52fc47d8087`.
- `README.md`: `ae88c82f00a17f8f4ec9fbfcbf6aefb3efe053a2434c2bd1f528afd5a70aaab5`.
- `wet-fixture-audit.json`: `16ca50a493bfe0a6b341e19fe6eb8a4c646b63863542cbb717980b0fea51d279`.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded point evaluation/inversion with actual provider identity and uncertainty propagation. Integration, moving-face thermal transport, total applied stress/work, wet/dry events and material sintering remain separately unverified here.

## Repository application binding

Independently diffed the applied source/tests against the reviewed isolated files. Production source changes only the first docstring to remove “Isolated”. Tests change their first docstring and replace the temporary importlib/sys/Path loader with the production package import; all test functions and assertions remain unchanged. Root reports the actual applied suite passed 11 tests in 2.18 s and preserved both its XML and candidate assets. The reviewer did not repeat unchanged wet tests for this application.

- Applied source: `2e05abfaf1ba135e4bd793e224bdefa87fbc5d5b261401f9b06303b70b94584d`.
- Applied tests: `3a460d7b8b4abba0e961c8895898d787f5d5325fa715c04097d3b5fb132fba03`.

Bounded APPROVE carries over to this exact application; integration-host support remains separate.
