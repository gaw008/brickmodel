# Source dry pressure implementation

Owned production files are source_dry_pressure.py, its tests, and the parent-authorized local shared-record extraction in source_inverse_pressure.py. No other production file, installation or Git commit was changed by this worker.

## Behavior and mathematics

`enclose_source_dry_pressure(storage, state, inverse)` returns a SourceDryPressure carrying the actual SourceWetStorage/state/inverse binding and a separate DryPressureContinuation. It requires exactly zero liquid, no liquid pressure, zero liquid volume, and the existing pure_gas_analytic_rounded mechanical path. Source, policy, available volume, caloric/cmin, saved energy error and inverse-temperature bounds are checked through the extracted common validator. The dry branch independently reconstructs the original represented closure residual/resolution, partial pressures, point bracket and zero-iteration evidence. Original fluid/global-volume/local-volume pressure lower bounds are retained using existing pure helpers.

For exact original inputs, T lies in [T-eT,T+eT] and V lies in [V-eV,V+eV]. The direct ideal-gas enclosure is [Ng R (T-eT)/(V+eV), Ng R (T+eT)/(V-eV)]. The original reported pressure error is retained in a second enclosure with radius eP + Ng R eT/(V-eV); the final enclosure is the hull of both. This retains the original pressure error and available-volume uncertainty rather than cancelling common terms or shrinking declarations. Both temperature and full candidate pressure intervals must lie in the original declared domains, otherwise the continuation is unresolved with no certified interval/radius. All arithmetic for enclosure endpoints is exact Fraction arithmetic.

Dry assumptions and qualification are independent of wet liquid-branch labels. source_certified, event_admitted and material_qualified remain false. This pressure calculation alone grants no dry transition or material applicability. Saved `.check()` does not call SourceWetStorage.evaluate/invert or RigidStorage.evaluate_at_temperature; tests forbid these calls after an actual manufactured dry inverse is obtained.

## Shared extraction and unchanged wet evidence

`_validate_source_inverse_record` contains the pre-existing source identity/metadata, inventory/target, caloric/cmin, source energy and error/eT checks. The old wet entry still separately requires Nl>0 and equality of liquid and total pressure. Its closure diagnostics, global/local pressure arithmetic, continuation inputs and output record are unchanged.

Before the extraction, capture_wet.py saved three complete manufactured wet pressure objects, excluding only the live storage reference while retaining storage identity. Cases cover T330/T331 and zero/nonzero available-volume error. wet-before.json and wet-after.json are byte-identical: 98,601 bytes, SHA-256 84fc11db47fd1f622417535d0dbe2f4cabb1d4f9128900e5a46c49c479075056. The old source file and both real capture runs are preserved.

## Actual verification

- Pre-implementation collection RED: missing source_dry_pressure module, retained in missing-module.log/XML.
- First implemented dry suite: 31 passed, 0.62 s.
- Final source suite: 33 dry-pressure tests plus all 31 existing source-inverse-pressure tests, 64 passed, 17.39 s; source-green.log/XML retained.
- Actual dry fixture uses source caloric/ideal-gas functions and explicitly manufactured geometry; the manufactured liquid seam and native EOS are not called during dry inversion. This does not count as a native source-material validation.
- Exact corner bounds, positive volume/input types, original error retention, forged source/state/mechanical/inverse fields, dict/MappingProxy identity, unchanged wet rejection, passive rechecking and full T/P domain exits are covered.
- All modified files parse with ast.parse and git diff --check passes. Ruff/mypy/pylint/Black/Bandit are not installed in the existing interpreter; no tools were installed.

FREEZE.json records exact current file hashes, original shared-source hash and real XML summaries. Independent review has been requested from the parent and is not self-certified here. No native run, installation or commit was performed.

## Independent provenance finding and narrow repair

The independent reviewer established two actual RED cases: an empty or fabricated fluid.source_ids tuple could pass when the aggregate SourceWetPoint labels were rewritten consistently. Pre-fix source/test/FREEZE copies are retained as before-fluid-source-binding*. The dry branch now reconstructs RigidStorage's original ordered source list from mechanical IDs, envelope IDs and nonzero gas providers in storage.gas_ids order, then compares the deduplicated exact tuple. The old wet validator and all pressure arithmetic are unchanged.

Two author regressions also exercise a reordered saved gas mapping, which does not change actual provider order. These plus existing actual-inverse/passive-check and saved-mapping tests passed in the targeted fluid-source-binding-green run (four cases). The unchanged 64-test batch was not repeated. The independent reviewer has been notified to rerun their two original RED cases. Updated exact identities and XML summaries are in FREEZE.json.
