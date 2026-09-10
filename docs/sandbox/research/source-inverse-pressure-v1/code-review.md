# Source inverse-pressure code review

Baseline `e0a7f4a962eddf0585244879cb44815010d4855f`. Reviewed the full new source inverse-pressure module and tests, the three arithmetic extractions, surrounding source/fluid storage and closure implementations, and the prepared saved-record runner. Production sources/tests were read-only for this reviewer. No native EOS evaluation, installation or prior whole integration-suite rerun was performed.

No confirmed unresolved defect in the final bytes listed in `FINAL.json`.

The three helper extractions preserve the original arithmetic ordering. In particular, pressure residual/resolution remains represented binary64 arithmetic; nominal liquid pressure error retains its directed lower compliance and outward numerator/quotient operations; volume uncertainty retains the global enclosure followed by local tightening, including the exact zero-volume-error case. Callers retain their original input/domain validation and subsequent acceptance gates. The helpers do not add physical evaluations.

An independent regression takes the exact pre-extraction statements from `git show HEAD` using AST extraction, without invoking the old full EOS methods. Fourteen cases compare binary64 bit patterns, exact Fraction outputs or exception type/message. Cases cover valid closure, gas-only closure arithmetic, nearly cancelling volumes, overflow, invalid gas volume, directed-bound underflow, nonzero and zero available-volume errors, global-domain failure and zero gas compliance. Actual result: **14 passed in 0.13 s**, zero failures/errors/skips. Original source snapshots and the executed test are retained alongside `helper-review.log` and `helper-review.xml`. Successful baseline branches were also directly inspected to ensure the comparison was not merely matching two extraction errors.

The new source bridge binds stored inventories, target energy, storage/source identities and source geometry, rechecks nominal caloric terms and heat-capacity lower bounds, and reconstructs the original closure/error arithmetic. It refuses underreported pressure/temperature bounds. The separately reported Python review's liquid-pressure/runtime-R binding corrections are present: saved liquid pressure must equal the same represented planar pressure, and the stored gas constant must match with exact runtime type as well as value. The final metadata correction was also read: source IDs must match the original source/record union and the source point's qualification, unknown fit error, solid volume and enthalpy metadata retain their original schema defaults. Input/result checks retain the original records and prohibit certification flag changes.

The continuation algebra first establishes the full declared-box bound before using a smaller pressure/temperature enclosure. Temperature-domain violations and failure to retain pressure-domain margin remain unresolved; no clipping or arbitrary lower-pressure substitute is introduced. The source caller requires positive liquid and gas inventories even though the standalone exact algebra supports the zero-liquid limit. Source and water temperature domains and the fixed closure pressure bracket are retained.

At trial level, the existing endpoint comparison is checked and retained. The new conditional pressure bound is an additional field; original N/U/T/reported-pressure gates, event-time status and full-inverse certification status are not overwritten. An absent explicit event policy leaves the conditional gate unknown. Passing the conditional pressure gate grants no source, material or event certification.

Scientific qualification remains conditional on the declared whole-domain response/error envelopes, stable smooth planar liquid branch and saved error contract. The current numerical envelope and nominal source Cp fit do not become an independently verified real-water or sludge-material uncertainty certificate. No new phase boundary, wet-to-dry transition or source event execution is implemented here. Actual saved-native execution and independent root-oracle results are separate evidence, not claimed by these fourteen helper tests.

The prepared runner is approved separately in `runner-review.md`; it explicitly permits two native reference-anchor constructions and forbids new endpoint/temperature-inverse/integrator evaluations.

Final installed interoperability correction: the actual saved dict and live HEOS MappingProxyType asset maps were falsely rejected despite equal contents. The narrowly scoped mapping-view normalization, strict built-in string-key check and eight independent passing tests are documented in `MAPPING_FIX_REVIEW.md`. All numerical arithmetic remains unchanged. The latest `FINAL.json` records source SHA `5695976e…`; the prior manifest is preserved as `FINAL-before-mapping.json`.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — scoped arithmetic extraction and conditional source-pressure accounting, subject to final byte identity.
