# Independent terminal saved-result review: native02

**APPROVE the saved V2 experiment against its original registered numerical gates.** The terminal artifacts support completion of the limited manufactured dry reference-half-plate native-energy/constraint-work increment. Native01 remains the separately preserved failed V1 experiment. This review performed no time integration, host call, model/evaluator call, or trajectory replacement.

The review binds `EXECUTION_FREEZE_V2.json` SHA256 `a30f6540e8703de7d2bc4f1b5e1ae8ec70f1b8d146aefd0295eab454591f2202`. All **351 registered files / 353 observed input identities** were independently rehashed against the saved before/after records and matched. The supervisor exited 0, reaped its child, recorded no timeout, and completed in **57.69992824998917 seconds**, below the unchanged 130-second limit. Both native results ended exactly at 10 seconds and stayed within their separate unchanged 60-second policies.

| Saved result | Coarse | Fine |
| --- | ---: | ---: |
| Accepted states | 2,023 | 4,023 |
| Accepted steps / StepLedgers | 2,022 | 4,022 |
| Actual RHS calls | 14,155 | 28,155 |
| Rejected trials | 0 | 0 |
| Native elapsed seconds | 16.671374708996154 | 33.225448000011966 |
| Exact original comparison times present | 101 | 101 |
| Maximum temperature difference from old fine T path, K | 9.814925761020277e-8 | 2.4562268663430586e-8 |
| Maximum temperature difference from independent old reference, K | 9.814959867071593e-8 | 2.456260972394375e-8 |
| Maximum per-cell energy residual, J | 1.2741717250534269e-13 | 2.5198087063344885e-13 |
| Maximum global heat residual, J | 1.115349132496668e-13 | 4.898308321454881e-13 |
| Maximum accumulated total constraint work, J | 2.620293113608728e-18 | 2.145618414227317e-18 |

Both reference-temperature maxima satisfy the original **4e-6 K** gate. The independently recomputed coarse/fine maximum difference is **7.358698894677218e-8 K**, satisfying the original **4e-7 K** gate. Every accepted prefix satisfies the unchanged absolute per-cell/global **8e-7 J** conservation limits. No threshold was adjusted.

## Independent recomputation

- All **6,046 accepted states / 6,044 StepLedgers** were checked for exact state/time/ledger alignment, constant float64 inventory bytes, unchanged energy identity, absent stretches, zero species exchanges and named mechanical-work component equality. Actual intervals do not cross an original comparison knot. Component sum residuals were recomputed and accumulated against the native result records.
- All prefix cumulative face heat, per-cell mechanical work, boundary heat, per-cell `Delta E-Q-P`, global heat residual and total constraint work were recomputed with `Fraction` from the represented binary64 ledger entries. Every published exact audit row and maximum matched.
- Each path's 101 comparisons maps to its actual accepted index and the original reference float time, bit-for-bit. Reference arrays were compared directly with the frozen old fine/reference files. No time reconstruction, interpolation or substituted state was used.
- **210 retained complete inverse records** were recalculated: 202 comparison records and eight final worst-witness records. At their actual returned float temperatures, exact original-binary-input internal energy, signed residuals, energy rounding bounds, free mean/strain, plate-evaluation discrepancy bounds and the public `residual norm <= temperature radius * reported dmin` certificate all agree. The residual balls lie within the same positive-capacity temperature rectangle. Initialization forward roundoff was checked separately from the zero target-input uncertainty.
- Both paths' unchanged policy values, their recorded successful/failed evaluation counts and all final gates agree with the independently computed quantities. All accepted-state decode summaries report their full actual state counts. The recorded instantaneous native-power reconstruction maxima are 4.0657581468206416e-19 W and 4.1335207826009857e-19 W respectively; they remain descriptive and have no new gate.

## Evidence limits and preservation

The full 42,310 per-RHS native rate fields were not archived. Their online summaries cannot be promoted to an independent field-by-field replay. The **81 periodic RHS witnesses** were checked to remain explicitly trial records with unknown accepted-prefix status at the time of logging. Full independent temperature decoding was not repeated for all 6,046 saved energies; the 210 complete inverse records above are the independently recalculated subset, alongside the frozen driver's accepted-state/RHS summaries.

Actual accepted-step counts are preserved. The repair branch was not counted in the runtime log, so no exact repair-branch invocation count is inferred from extra panels.

All native02 artifacts hashed before and after this audit remained byte-identical. The seven independently bound native01 artifacts also remain unchanged and its `passed=false` is retained. The original and V2 protocols remain separate. Material, chemical-mass, source-material and full-cycle qualification remain false; the result does not qualify real sludge parameters or a complete wet-to-fired production process.

The standard-library reproduction script is `audit_saved_results.py`; detailed independent values and original artifact hashes are in `SAVED_RESULTS_AUDIT.json`.
