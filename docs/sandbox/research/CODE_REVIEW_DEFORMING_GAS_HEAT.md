# DeformingGasHeat independent physics/code review

Verdict: **APPROVE**, limited to prescribed, pressure-matched ideal-gas chamber actuators and explicitly manufactured boundary-relative transport. This is actual gas/heat/work coupling, not solid-skeleton or sintering mechanics.

## Source and physical contract

Read the complete new host, applied motion provider, gas evaluation extraction, existing transport/work integration contracts, `DEFORMING_HOST_DESIGN.md`, and the full new host tests. Exact GasHeatModel type excludes custom inherited body-power/lab-frame operators. Explicit mechanical regime, work identity/sources and host manufactured permission are required. Reference cell count, area, each width and full gas volume are bound through the reviewed 2-ULP construction contract; equal volumes with different shapes fail. No solid/liquid/pore phase is silently subtracted.

Each evaluation checks the original base caloric signature **before** dataclass replacement, preventing mutated source/caloric settings from being legitimized by the instantaneous copy. Replacement updates current area, all widths and gas volumes together; unchanged extensive N/U then produces the actual temperature, pressure, concentration and current-volume kinetic source. One gas evaluation supplies both transport and the pressure used for work; no extra thermal inverse is called merely to obtain pressure. Immutable diagnostics retain the sampled geometry, decoded gas states, pressure/work arrays and source identities.

Mechanical power is `−p_i Vdot_i`, including the tangential-area term already checked in the motion provider. Compression is positive work into the gas. With unequal chamber pressures, separate internal actuators can supply nonzero net work even when total volume rate is zero; forcing cancellation would be incorrect. Equal-pressure normal redistribution cancels as the separate sample demonstrates. Face enthalpy retains donor flow work and is not augmented by a second pQ. Mechanical work is supplied once in `cell_power_w`, so the existing accepted-stage quadrature stores it in `cell_work_j` alongside the face ledger. Existing gas body power must be zero; an unexplained additional source is rejected.

Motion-domain errors become controlled DeformingGasHeatError/IntegrationError, while physical thermochemistry domain errors retain DomainExit. Arbitrary unexpected Python errors are not broadly swallowed. Empty work-source validation now consistently translates the original IntegrationError while preserving its cause. ReferenceGeometryAlignment has its explicit concrete type. The exact-type/manufactured gate and source declaration are a limited model contract, not material parameter verification.

## Independent references and meaningful coverage

The closed constant-Cp benchmark derives from fixed N and dU=−p dV: Cv=30−8=22, T=500*(V0/V)^(8/22), and (P/P0)*(V/V0)^(30/22)=1. Its `imposed_normal(t)` computes the prescribed polynomial directly, without calling candidate.sample or using evolved temperature to manufacture a target. Formation offsets cancel in energy differences. Thus the temperature, pressure/invariant and energy targets are independent of the candidate's work calculation; the prescribed mathematical motion itself is shared by specification.

Other tests cover pure tangential work, current-bulk **second-order** reaction (avoiding a first-order volume cancellation that could hide the bug), donor enthalpy counted once at an open boundary, deep immutable arrays, caloric mutation, same-volume wrong shape, unequal-pressure two-cell shared faces, and zero-motion Rates/trajectory identity against the fixed host. The two-cell test reconstructs every cell's full N/U prefix from raw accepted ledgers and compares global energy with actuator work. Cancellation and resource termination preserve accepted prefixes. These short manufactured tests do not establish convergence for arbitrary reacting deforming networks or a material law.

## Actual independent execution and artifact checks

Ran 14 host + 29 motion + 4 gas-evaluation tests once: **47 passed in 4.87 s**, XML `/private/tmp/deforming-gas-final-review.xml`. No wet/EOS or full installation suite was repeated. A temporary reviewer pytest hook observed the same three adiabatic integrations and asserted **every accepted step** had exactly its declared dt: 1/128, 1/256 and 1/512 s, with 256/512/1024 steps over 2 s. These checks appear as `INDEPENDENT_ACTUAL_GRID` in the XML; fixed-step evidence is not inferred solely from counts.

Independently parsed the author's `deforming-gas-host-attempt01.xml` and the reviewer XML. Both contained the same three-row ADIABATIC_REFINEMENT_EVIDENCE, exactly matching the saved metrics JSON. Recomputed adjacent temperature-error ratios from the rows:

| dt (s) | Actual steps | Maximum T error (K) | Error reduction |
|---|---:|---:|---:|
| 1/128 | 256 | 0.0006784491126836656 | — |
| 1/256 | 512 | 0.000169571820379133 | 4.000954351771254 |
| 1/512 | 1024 | 0.00004238796759636898 | 4.000470652281493 |

Finest relative-pressure and isentropic-invariant errors are both 7.8168645112342e-8; maximum energy-oracle error is 0.0009325349615210143 J. These satisfy the original finest gates of 2e-4 K, 2e-6 relative, 5e-3 J and ≥3 reduction per halving. Coarse errors are retained rather than relabeled as satisfying finest requirements. All selected ordinary control, independent oracle and ledger assertions ran; no error threshold was loosened by the reviewer.

## Final bindings

- Host source: `22cf6b78eaab05f6090059b27332f53bd4747f4195dd46165f68121be5ddce5b`.
- Host tests: `4438138564fb51821736e82430dfe41d6336a2b9085a71502d0caa51590ba4c5`.
- Motion source: `bed652b4c5b1670cd7122d08d331fd7b15f970b0f12fcba2eff37095249253dd`.
- Gas evaluation source: `b14d4c6b22fa06d6d499868b6c24e909a3ba960cee552c58df6023696bc69cf3`.
- Author XML: `b086ddeced290ad357ff4e3412cf985c0b7540c609cd3c956c61567591b33a7e`.
- Author metrics JSON: `2d25637d0dedfffd308669c240281394fdd6278474ee2edbc24ffd93d72a1cb8`.

Only this review was written for the present task; no production source/tests were edited and no Git commit was made.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — the declared actuated gas-chamber slice passes independent code review and bounded analytic/shared-ledger validation. It does not validate real brick shrinkage, solid stress, phase-dependent mechanics or a free-sintering constitutive law.
