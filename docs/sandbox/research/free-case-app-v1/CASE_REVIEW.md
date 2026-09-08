# Independent frozen free-case review

Verdict: **APPROVE**. No blocking code findings in this bounded candidate. Review was read-only against the actual repository; `before.py` is byte-identical to the current production `verification_case.py`. No EOS, tests, installs, or repository edits were performed.

## Inspected SHA-256

| Candidate file | SHA-256 |
|---|---|
| verification_case.py | e471398ba380a941aa4864ad7b7fd6b9342d660a47ddac897d9f7ccdb4642a34 |
| candidate.patch | 0cd532d5027393616e3e75a0f258e7b02f7cbaf6381c935a5ba8ff041eb0a96e |
| test_case.py | e8d3b54b5bbc23cfc66cdc9500823370c5e3f4ef99ad4e4dfa348d4ee6cd5fb3 |
| reacting-wet-free-slab-v1.json | f39c6a1ae42853c2bb6435143419785981bbdbfe9a1eb210904145f506ac990f |

## Reviewed behavior

- Lines 74–89 and 137–149: explicit free model ID selects a separate exact mechanics key set and required stretch tolerance/scale. Prescribed motion keys cannot silently enter the free model. Existing prescribed keys remain intact.
- Lines 202–231 and 258–267: finite binary64 validation and positive free viscosity are retained; positive initial stretches must lie in the declared domain, external pressure is nonnegative, and free time integration requires an ordered interval without manufacturing a motion schedule. Ordinary integration policy is built directly from explicit values; refinement only halves its two existing step settings.
- Lines 437–470: the free branch constructs actual reacting `CurrentSolidStorage` points and `FreeSolidSlab`, with matching explicit reacting regimes. Composition weights remain beta/V0; micro-interface area remains density times V0. Parent error budgets scale by parent_cells/cells, as do inventories and reference volume. No extra reaction heat or prescribed mechanical rates are introduced.
- Lines 479–501 and 507–547: initialization passes the complete normal vector and common tangent to every point, applies uniform-profile mapping consistently, and retains the forward mechanical vector when conservatively reconstructing energy. Existing exact Fraction parent/child inventory and energy checks remain, together with source-enclosure checks on forward storage discrepancies.
- Lines 550–617: snapshot evaluation uses the actual current host and current transport geometry. The free branch emits the numerical geometry and free-rate solution instead of accessing nonexistent motion. Inspected `CurrentSlab`, `FreeSlabRates`, `SkeletonEnergyState`, and thermal record fields contain encodable state data; the selected snapshot does not encode the live host, point storage, inverse current-storage object, or provider graph. Existing source binding and initial inverse-temperature enclosure checks remain.
- The production prescribed construction path is unchanged apart from branch dispatch and passing through its existing absent mechanical vector. Tests compare its source IDs, energy identity, rows, and temperatures with the original implementation.

## Evidence limits

The three supplied tests cover parser separation, actual dry two/four-cell construction and conservative mechanics, error/interface/composition scaling, and the old builder path. The dry wiring test explicitly substitutes the zero-water caloric path and does not establish native water qualification. It does not execute `snapshot` or an ordinary integration trajectory. The implementation report openly records those limits; native build/snapshot and application service/catalog admission remain parent-owned follow-up work. This approval does not claim those later paths have run, nor that the manufactured sample validates a real material or firing cycle.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: **APPROVE** for the frozen candidate and stated scope.
