# Fixed-domain spatial scaling initial review

Reviewed scaling_check.py SHA256 `0b4fac07f52b30aba313354718c7d3bf24117340e38b6eac87030e8723ab6c01` and actual installed-API source contracts in geometry/skeleton_energy/reacting_skeleton_energy. AST parsing only; no imports, tests, EOS or scaling execution by this reviewer. Later spatial fixture/ledger scripts are pending separate review.

The two-versus-four-cell comparison keeps physical reference domain .02 m x .01 m2 fixed. Child reference volume, interface area, A/B inventory and lumped phase conductance halve; composition weight doubles so q=1+wB is unchanged. These represented halves are checked with exact Fractions. Energies, fixed-composition powers, dissipation and Rayleigh power are extensive and use factor 2; Piola responses and composition energy derivatives are intensive and use factor 1. This classification agrees with the actual API: E_ref scales with cell volume/area and dE/dN=E_ref*w, preserving the product under half-volume/double-weight scaling.

Every actual API numerical-bound entry is compared using exact rational represented differences against summed parent/child bounds. The independent interface-energy expression uses exact binary input values and the actual tangential area law. B=0 plus two nonzero B states prevent q=1 from hiding bad scaling. Negative controls deliberately retain child wB=10 and require a resolved interface-energy mismatch; thus the test can detect failure to scale composition weights. Three deformations include undeformed, isotropic compression and anisotropic motion with nonzero rates.

Phase conductance and first-order reaction extensive scaling are clearly labelled analytic assertions only; neither phase nor reaction API is evaluated. The script does not claim native water, transport, full reaction coupling or material/grid convergence validation. It invokes only the actual installed skeleton API with an explicit manufactured provider identity. Loaded modules are checked after the run against source bytes and recorded; execution must retain root's frozen-source condition since the script does not independently take before/after source manifests.

Failure retains partial numerical checks/negative controls and traceback with nonzero exit; existing result is protected. Result JSON serializes check scalars rather than arbitrary provider objects. No blocking inconsistency found. A helper operating solely on the local generated result cannot establish a broader source-qualified model by itself.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE bounded no-EOS actual-skeleton scaling check. Spatial fixture, ledger adaptation and native execution require their own final review; no such approval or result is claimed here.


## Four-cell ledger adaptation

Reviewed exact delta from the approved two-cell auditor and AUDIT_POLICY.md. New auditor SHA256 `3b48cd7875f631a8e58396cb52d5f7f3f4da280e14de8fc961a914a4dc551bb9`. Cell loops/cumulative arrays are expanded to four, face shape to five, and external boundaries are indices 0/4. Shared internal faces cancel by the correct telescoping sum over all four cells. Nonzero internal flux indicators scan all three internal faces rather than only the center face. Existing per-cell species/energy/component and global water/carrier/energy checks remain.

Every stated local extensive tolerance is halved exactly: species 5e-13 mol, energy 5e-8 J, carbon 5e-11 mol and analytic A 5e-10 mol. Global water/carrier 1e-12 mol and energy 2e-7 J remain unchanged. Four local energy budgets sum to the same global energy budget; no hidden gate relaxation is present. Existing failed-audit partial prefixes/input hash/traceback and nonzero exit remain; new output-overwrite guard preserves earlier evidence. This is still a prefix auditor, requiring separate solver/horizon/source/mode acceptance checks.

Verdict: APPROVE four-cell saved-ledger adaptation under the frozen audit policy. No execution, EOS or source modifications performed.


## Conservative grid-comparison and archive review

Reviewed compare_grids.py SHA256 `d104ed526ddc33c631d50feea205d1bb3b0111498bb884638be2cf068fdb274b`. It requires all four source runs complete, ledger audits bound to exact result hashes, matching horizons and own initial/final state records. Parent-pair initial species and total energy are conserved exactly as Fractions; paired current widths and common face area establish the same physical domain for aggregation. Corresponding water implementation/assets and time-control policies must match. Within each grid, initial state is exact and both initial/max time steps halve.

Endpoint amounts and total energies are summed over fine child cells before comparing with their coarse parent. Both signed spatial discrepancies and signed within-grid time-cap discrepancies are reported separately. No arbitrary mesh-pass threshold, Richardson order or convergence certification is introduced. Temperatures and inverse bounds are averaged only as an explicitly qualified equal-reference-volume diagnostic, not decoded from aggregate energy. The discontinuous field/two-grid limitation is stated. Source/physical coefficient constancy still relies on separately reviewed frozen fixtures and supervisor evidence; this comparator does not replace the source audit.

Failed input/identity/pair checks retain partial report and traceback and exit nonzero. Existing output is protected. Numerical comparison completion does not mean any particular discrepancy is resolved or acceptable. No execution performed; approval is conditional on the new fine-grid runs and independent ledgers actually completing under the registered inputs.

Archive helper SHA256 `bb16969651c8c8cbc98859a3973cdacf95028e030a3fd97ecec56494258c762a` differs from the previously approved helper only in SOURCES selection. Original-byte/hash reread, failure preservation, fresh destination and terminal-supervisor checks remain. Approve only after all selected-source EOS/audit/report writers terminate and freeze; no archival execution performed here.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE saved-grid diagnostic and archive adaptation with the stated runtime/freeze prerequisites. Fixed-spatial fixture/scripts remain pending final review.


## Frozen native fixture review and constructor finding

Read full fixture/callback/wet_run/run and their source contracts; git diff contains only root documentation work. PLAN reviewed at 4c045829c908adc9b7fcaac0f4ab6aa03aae63d68555ec3b3e38031da46c01c2. No imports, tests or EOS executed.

[HIGH] Four-cell transport construction retains oversized template pore volume.
File: /private/tmp/brick-fixed-spatial-v1/fixture.py:84
Issue: test_rigid_storage.model creates a 1e-4 m3 available pore volume. make_model passes that unchanged into a RigidFluidHeat with .01 m2 area and .005 m child width, only 5e-5 m3 bulk. Its actual __post_init__ guard at src/sludge_sandbox/rigid_fluid_heat.py:174 raises cell_available_volume_exceeds_bulk_or_unresolvable_width before later SolidFluidStorage construction. All four-cell native callbacks would fail before initialization.
Fix: scale the fluid mechanical template volume by 2/cells before constructing the transport, preserving the parent scale=1 identity, and refresh the preregistered fixture hash before execution. Parent and worker informed; final patch review pending.

Other reviewed contracts are consistent: actual forward/deformed storage attributes exist; extensive inventory/volume/interface/rate scaling, q weight scaling and current reaction storage binding are explicit; no phase or reaction disabling. Callback records numerical evidence before downstream numerical checks. Parent replay/pair checks currently fail before richer returned evidence, but failed status and traceback survive and prevent acceptance; richer diagnostics are optional, not an additional blocker. Wet execution requires fresh matching cells/profile callback, exact initial state and initialization, and source energy identity; full run is serialized before completion checks. Original 120 s/100-step internal and 30 s callback/150 s wet external bounds remain. Supervisor prevents overwrite and binds source/tests/water/script/preregistration/callback inputs.

## Independent all-face auditor review

audit_faces.py SHA256 60d5cb2fc94574fc0a0d91d0e7976b79595d78af790d6f8f969539e39e36b7f9 approved for saved-JSON arithmetic only. Exact delta from prior approved audit_callback.py retains the 1e-12 relative plus 64 sum-ULP policy, gas N/V reconstruction, face-normalized mixture, series diffusion, mass-frame carrier correction, Fourier heat and sampled common-face-temperature enthalpies. It loops all cells and all ordered internal faces with each current half-width; verifies exterior zero flux and immobile columns. Central gradient face must be nonzero while identical child pairs and uniform profile require zero flux. Input hashes, partial checks and failed traceback are atomically preserved with nonzero exit. No native or audit execution by reviewer.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 1 | pending fix |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: WARNING — fix the deterministic four-cell constructor failure before native execution. Independent saved-data face auditor approved.


## Final constructor fix verification and native approval

Exact delta against preserved preflight-original/fixture.py inspected. Fluid template mechanical.available_pore_volume_m3 now multiplies by scale before transport construction. At four cells, 5e-5 m3 equals the reference transport bulk; at two cells multiplication by 1 preserves all values and the parent identity. Actual SolidFluidStorage._fluid still constructs current pore volume from actual current bulk minus solid volume; the fix introduces no second scaling there. PLAN delta contains only prepared fixture hash and explicit preflight-correction provenance; original fixture and plan are preserved. No other script changes. All four scripts AST parse; no imported modules, EOS or tests executed.

Final approved SHA256:

- fixture.py: 66639ad99b1996a83a1836c58a4b6ca01b59ebcbe88de13a3ae899b973972e77
- callback.py: 049d4eb4c23ab4666684b33b1b2481d85e280afe1f785da56594bda3ad13bd96
- wet_run.py: 0a5304cdd1659889b030b4aa81b26f473aca19b7f9f163f50ffc6b939fdcb9f9
- run.py: 1f02980049a6fa49765f51e506b0fab3297b2a13c89c9774bd2ff96c4f495a5d
- PLAN.json: 1ad81a3b7f656bef00218abd29ef72441e76d4d907754e2f1c6e06b95817d81d

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 open, 1 resolved | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE bounded native callback under frozen source/input supervision, then fresh-callback-gated wet runs. Saved-JSON face audit separately approved. Approval is static; no native result or spatial convergence is asserted.
