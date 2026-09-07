# Stage6 preregistered child review

Initial disposition: fix the identity comparison before execution. No EOS/test/production edit performed; source diff, AST and archive hash inspection only.

[HIGH] Tuple/list mismatch makes intended identity inequality vacuous.
`initial.energy_model_identity != previous['energy_model_identity']` compares a tuple with a JSON list; it succeeds even with identical identity content. Compare `enc(initial.energy_model_identity)` to the previous list and also require the initial identity match the actual operator identity. This is an evidence-gate defect, not a change to physics.

Other inspected conditions pass:

- `original-child.py`, `entropy_reference.py`, and `previous-result.json` are byte-identical to archived original child, oracle and successful refinement result respectively. Oracle SHA is d61e40dc96253394e534123daf578a45eb288da82b8853fd017dd44fcd03c323. Both Python files parse.
- Child diff preserves fixture construction, motion, endpoint, step/control/resource policies, inverse policy, Fraction ledger reconstruction, oracle constants/root tolerances and every endpoint comparison gate. Inverse remains1e-6 J/1e-6 K, endpoint2e-5 K/.2 Pa and component1e-6 J. No stage5 inverse tolerances were substituted.
- Tested host uses explicit public HEOS loader/pinned manifest. A separate default Python WaterProperties feeds the unchanged exact-type-checked entropy oracle and all native water u/s operands for pore truth. Scientific reference truth does not call HEOS storage or its inverse.
- Initial energy is neither overwritten nor rounded. PLAN explicitly replaces the historical whole-object exact equality by exact inventories, native-generated energy difference<=1e-6 J and intentionally distinct implementation identity at common300 K/geometry. This is correctly described as a new cross-backend initial comparison, not the old exact N/E/tag test.
- Original four-step0..1/64 s scope of the one-second10% motion remains; partial fixed-inventory compression is not active phase transfer, depletion, full wet trajectory, general material proof or performance evidence.

Recommended evidence additions: explicit reference provider class/implementation=None/reference/assets, loaded module paths and initial oracle gas volume. Current saved native u/s and original reference equations already permit the main pore-work audit; gas volume saves avoid tiny alternative-reconstruction roundoff. Supervisor input list must include all test helpers, child/oracle/prior result, pinned manifest and source files, with unique attempt status/logs. Result approval remains contingent on actual terminal evidence and original scientific gates.

## Frozen pre-execution follow-up

**Approve execution of this bounded attempt.** Reviewed the corrected child: new/old identities now compare after enc normalization, and initial identity must equal the actual operator identity. The HIGH finding is resolved. Separate reference provider is asserted exact Python WaterProperties with implementation=None; its scientific reference/assets and loaded sludge module paths are saved. No energy rewrite was added and all original physical/numerical policies remain unchanged.

Reviewed run.py: unique attempt01 via the previously reviewed supervisor, explicit repository src and test-helper PYTHONPATH, isolated child path and working directory,30 s external timeout. Input hashes cover all current src modules, test helpers, water assets, local Python/JSON files including plan/oracle/previous result, and supervisor source. No alternative EOS process is launched by this reviewer. Scientific success still requires actual terminal exit and complete original gates; this is execution approval only.

## Initial dependency failure and separate attempt02

Attempt01 actually failed/exit1 in0.488418208 s with inputs unchanged. Retained stderr identifies missing pytest during import of the test helper, before the child's provider creation/try block; no scientific result was produced. This is not a failed thermodynamic gate or a successful scientific attempt. Dependency-repair.json records an offline pytest8.4.2 repair; independently read installed dist-info metadata confirming pytest8.4.2, iniconfig2.3.0, packaging26.3, pluggy1.6.0 and pygments2.21.0. The installation command itself is Root's execution evidence, not rerun by reviewer.

Verified child remains SHA367171ea25a0142fe5db0f01803f5319bf7768b0210966b93cd38cbc3a679e6b and run02 differs only in fresh attempt02 directory (plus trailing whitespace). No policy/kernel/oracle change accompanies the dependency repair. Attempt02 scientific outcome remains pending at this audit point.

## Attempt02 terminal audit: incomplete resource-limited prefix

**FAILED / incomplete; no four-step wet-prefix qualification.** Actual supervisor failed/exit1 in28.734425500 s, not an external timeout. Child retained status failed/AssertionError wall_time_limit. Integrator reports resource_limit/wall_time_limit after26.853374791 s,10 evaluations, one accepted step and zero rejected trials, with times[0,1/256]. Only two states and one ledger were saved. The25 s integrator budget is checked at operation boundaries and was exceeded by an in-flight evaluation; this does not mean the external30 s cap was increased.

All recorded before/after input hashes agree and match current files. Independently recomputed initial energy difference: -482640.5381991861 minus archived -482640.53819918627 =1.7462298274040222e-10 J, within the preregistered1e-6 J initial gate. Inventories are exactly unchanged. New initial tag matches actual operator tag and differs from the historical tag after normalization. Reference provider is recorded exact Python WaterProperties/implementation None; all saved sludge module paths resolve to the repository src tree.

Failure occurs immediately after integrate returns, before the independent accepted-prefix reconstruction and Python entropy endpoint. Saved python_oracle_state_tp_calls is0. Therefore there are no new independently reconstructed prefix/component or endpoint T/P comparison results, and no basis to claim the original four-step scientific gates passed. This is a cost/resource failure, not a measured endpoint accuracy failure; zero rejections is not successful completion. The historical Python four-step result remains separate evidence, not a substitute for this incomplete HEOS attempt.

No tolerance/time-budget relaxation or automatic retry is recommended. A separately identified, bounded single-evaluation profile can diagnose cost but cannot count as this trajectory's completion or as an end-to-end performance result. Production remains unchanged by the reviewer.

## One-evaluation profile audit

Profile-child setup through initial comparisons is AST-identical to the reviewed child; only the integration/oracle tail is replaced by cProfile around one actual op.evaluate(initial,0). It writes separate profile-result.json/profile.txt/evaluate.prof. PROFILE_PLAN accurately declares instrumentation overhead and diagnostic-only scope. Profile-attempt01 completed exit0 in4.560480542 s, and all recorded inputs agree before/after/current bytes.

Saved profile reports154430 calls (153900 primitive),2.717 s profiled total,205 kernel state_tp calls and410 transaction contexts (820 generator entry/exit resumptions). Transaction cumulative time2.648 s contains JSON encoding/decoding and native JSON retrieval. JSON iterencode self time1.077 s and decoder approximately.610 s are major subcosts; transaction self time.937 s includes other work, including native fluid-definition retrieval. Nested cumulative times must not be added. This supports identity-validation overhead dominating this measured evaluation; it is not a standalone pure-EOS speed measurement. profile.txt SHA: db8e5195dff06a8c974cfce4c694d1822be2b8afbbb2ff036542b4488f864ebc.

Reasonable next isolated single-variable candidate: constructor already validates both original raw-fluid SHA and canonical parsed definition; runtime before/after checks may compare the current raw bytes SHA against the frozen validated raw SHA, eliminating repeated Python parse/canonical serialization without changing numerical gates. This is stricter for formatting changes, which should fail rather than silently adopt a new representation. Preserve before/after read, lock, warning and config checks. Do not simultaneously remove nested transactions; that would change a second behavior and complicate attribution. Bind the changed kernel/manifest and retain this failed baseline before any bounded measurement. No such optimization or retest was performed by reviewer.
