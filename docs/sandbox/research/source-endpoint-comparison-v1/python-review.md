# Independent Python review — source endpoint comparison

Approval: no critical or high findings in the reviewed bytes. Read-only review; no production/test edits, native property calls, provider construction, installation, or commit performed by this reviewer.

Reviewed production: `src/sludge_sandbox/source_endpoint_comparison.py`, 7,195 bytes, SHA-256 `a4927606c0c7392cde4b93c2e972ea9c02ba461d459caae1530a78c3aea90d77`.
Reviewed author tests: `tests/sandbox/test_source_endpoint_comparison.py`, 8,601 bytes, SHA-256 `c1730039a394d9e36f4e0c8653a29bf53b2fb0a51ff20f4684e3505facafb0c3`.

The original complete DepletionPolicy is detached and recursively revalidated through existing `exact_record.pack/unpack/_policy`; canonical packed text binds the complete outer and nested policies. This reuses the existing policy codec rather than maintaining another recursive framework. Existing `source_prefix_trial._policy_binding` would not by itself detach nested dataclasses. The resulting policy copy preserves typed Fraction fields in pressure boxes and rejects invalid nested configuration.

The new trial entry first invokes the existing SourcePrefixTrial check, retaining the completed-reference and recoverable DomainExit replay requirements. The arithmetic entry validates two saved samples with existing source binding logic, uses exact Fraction differences and both inverse error terms, and checks the four N/U/T/reported-P thresholds independently. Reported-temperature pressure remains distinct from full inverse-temperature pressure. Same exact endpoint time is explicitly not event-time admission. No event, material, correction, mode transition, or new physics operation is executed.

Independent execution: **15 passed, zero failures/errors/skips, XML time 0.451 s** (`focused.xml`, `focused.log`). The selected native input was SHA-pinned to `7c0907af104450ffc42cf142e3e3aebefaf21c597eb6806f09b7bdbe6d6d3505`. Seven existing source/property entry points were blocked while the old fixed passive decoder restored terminal sample data. Checks covered:

- Detachment and exact reconstruction of the complete nested event policy, including a pressure-comparison parameter box.
- Six invalid nested-value cases across roundoff, nested-approach, pressure schema, and Fraction volume errors.
- All three saved native endpoint cells and independent exact T/P interval arithmetic, without new property calls.
- A manufactured arithmetic perturbation with bound `1 + smallest positive binary64`, proving the result remains strictly greater than 1 although converting it to float gives 1.
- Strict fixed dry mass types, post-measurement source mutation, exact Fraction result type, numerical-result and qualification tampering.

These independent probes exercise passive measurement/policy behavior. The parent owns actual new trial tests (including reference recovery and each independent gate) and integrated validation; this note does not claim those tests were independently rerun.

The initial probe run had one reviewer-harness error: attempting deepcopy of a saved record containing MappingProxyType. The harness was corrected to create explicitly replaced dataclass records. `first.xml`/`first.log` preserve that event; it is **not a product RED or a fixed product defect**. The final source already enforced exact float dry masses during both runs.

Both changed Python files parse successfully. Ruff, mypy, pylint, black, and bandit are absent in the existing review interpreter; no tools or dependencies were installed. The required tracked Python diff was empty at first inspection because both additions were untracked; the full files were read directly. `review-state.json` records actual reviewed hashes and XML counts.

Saved-native restoration scope: the existing source-net-panel replay decoder already restores the terminal ConservedState/SourceExactEvaluation graph passively. It does not restore full SourcePrefixTrial: the saved trial intentionally omits its adapter and trial.check requires an actual ExactSourceColumn. The implemented saved-pair entry is therefore the appropriate minimal reuse. Existing native trajectory audits remain separately bound supporting evidence; no synthetic live adapter or resume authority is implied.
