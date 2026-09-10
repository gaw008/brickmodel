# CurrentSlab identity adapter candidate — not applied

The repository is unchanged. `candidate.patch` adds two imports and one exact-type CurrentSlab branch to the existing `_canonical`, immediately before generic dataclass recursion. Complete candidate module is `deforming_solid_storage.py`; unchanged repository source copied to `deforming_solid_storage.before.py`.

## Contract

Only an exact `CurrentSlab` record gets array support. Its seven known field names must match the current declared schema exactly. `widths_m` establishes positive cell count N. Every field must be an exact numpy ndarray with native float64 dtype, one dimension, finite entries, and shape N except faces_m/face_areas_m2, whose shape must be N+1. Empty, object, float32, nonfinite or malformed arrays are rejected with DeformingStorageError.

The canonical record retains the original CurrentSlab module/type tag and all seven named fields. Each field stores an explicit float64-array tag, shape and every binary64 float.hex value, including signed zero. No private field, cache, compare=False field or numerical value is skipped. Array strides, writeability and allocation address do not change physical values and are intentionally not included. Existing geometry checks retain responsibility for geometric consistency; identity serialization itself does not certify a physically compatible slab.

All previously supported types use unchanged original branches. Unknown bare or nested ndarray remains unsupported; CurrentSlab subclasses do not receive the new admission. The adapter does not add arbitrary array serialization.

## Imports and recursion

`geometry.py` imports dataclasses/math/numpy and has no reverse dependency on deforming storage. `deforming_solid_storage` already reaches geometry through deformation_program; direct CurrentSlab import therefore introduces no import cycle. Numpy is already an existing dependency in this path.

The exact CurrentSlab branch encodes numeric arrays directly and terminates. Generic dataclass recursion remains unchanged and visits every field, including `PrescribedSlabMotion._reference_state`. Other cyclic user-created object graphs remain unsupported exactly as before; no general graph serialization or reference-elision scheme is introduced.

The temporary test harness imports the candidate module under an isolated module name, aliases its exception to the existing repository exception, and monkeypatches only the original module's `_canonical` during actual current-halfcell and content-change tests. This simulates the local source patch while letting all existing `_digest` import references continue using their original function globals. It does not replace storage classes, solve another physics problem, or mutate repository files. A real application would naturally retain the existing exception type and module globals; no runtime monkeypatch belongs in production.

## Evidence

- `RED.log`: original actual `test_actual_current_halfcell_surface_single_inverse_and_original_errors` fails on cached reference slab ndarray identity, before any candidate patch.
- `GREEN.log`: **13 passed in 0.35s**, process terminal exit0. The same original test now runs its actual dry total-energy inverse/current surface and forbids native water EOS calls. No long integration suite or native EOS scan was run.
- Every one of seven array fields changes identity under a one-ULP value change; same-shape field swaps change identity. Wrong shape/dtype/nonfinite arrays and unknown ndarray remain refused.
- Changing the private `_reference_state.widths_m` after constructing the actual programmed/deforming operator triggers `runtime_programmed_operator_content_changed`; cached arrays are not omitted.
- `old-golden.json`: existing RigidFluidHeat slab, nested scalar/Fraction graph, and actual WaterProperties canonical payloads/digests remain exactly unchanged.
- `GREEN01-test-harness-failure.log`: initial test-only failure was a non-frozen dataclass subclass of frozen CurrentSlab. Corrected only the test subclass to frozen=True; candidate implementation stayed unchanged.

`FREEZE.json` binds candidate, baseline, tests, logs, patch and golden evidence. No installation, repository application, commit or material admission is claimed. This repairs an existing identity-representation blocker; it does not weaken physical validation, skip source hashes, supply missing material properties or admit any new moving geometry.


## Actual application and installation

The reviewed candidate was applied byte-for-byte to src/sludge_sandbox/deforming_solid_storage.py; the reviewed formal test was copied to tests/sandbox/test_current_slab_identity.py. Final source and formal-test identities match the reviewed freeze. The preceding candidate-only descriptions above are historical.

Source run: 31 passed, 1 failed in 3.17 seconds across the formal identity tests, full deforming-wet-admission and programmed-free-slab files. The original actual current-halfcell/single-inverse test now passes. The one failure is the older `test_active_chemical_core_and_dry_policy_match_pre_admission_source`, whose whole-method AST expectation predates WaterPhaseTransfer.evaluate factoring. WaterPhaseTransfer was not edited here; actual source and prior HEAD both have git blob a260c366aec47eaea5d9c1917bca27945f9bb996. This test failure is preserved and remains to be resolved with meaningful behavioral coverage, not by changing the water model or silently replacing an expected snapshot.

Noneditable installed execution from /private/tmp, without PYTHONPATH: all 12 formal identity cases plus the original actual moving-halfcell regression passed (13 passed in 0.48 seconds). All 107 installed Python modules byte-match source. No full-suite PASS, new water-physics validation or raw-sludge qualification is claimed. The patch restores supported moving-host configuration identity while preserving every CurrentSlab cached value and rejecting unrelated arrays.

Read-only follow-up mapped the old interface checks and chemical loop to the extracted helpers exactly; dry/depleted logic and source-matching constructor loop are also unchanged. The later return includes previously introduced mechanical-rate and dynamic-source forwarding, so this is not described as purely renaming a method. STALE_WATER_TEST.md records the next legitimate-host behavioral regression to replace the obsolete whole-method snapshot. No water source or expected snapshot was modified in this increment.
