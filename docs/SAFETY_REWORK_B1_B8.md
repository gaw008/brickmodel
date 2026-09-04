# Safety rework B1–B8 evidence map

Scope: research-only synthetic MVP. This document does not approve production recipes, emissions/compliance claims, kiln-speed control or any PLC/robot/kiln connection.

## Code and regression-test map

| Finding | Implemented behavior | Primary code | Regression evidence |
|---|---|---|---|
| B1 phantom dimensions | Wet-feed water enters wet mass/effective heat capacity and reaction potential; PSD/morphology enter permeability and transfer; oxide chemistry enters an explicitly unresolved liquid screening proxy; feed density/cp/k/effective gas diffusivity are mixed into the forward model. The inverse transform has exactly 12 physically coupled coordinates. | `models/common.py`, `chemistry/stoichiometry.py`, `inverse/transforms.py` | `test_feed_moisture_morphology_and_oxide_fingerprint_are_not_phantom`; `test_every_inverse_coordinate_changes_an_interpretable_physical_quantity` |
| B2 oxygen-limited chemistry | Organic oxidation uses zero multiplier at zero O2 and is capped by initial pore O2 plus the time-integral of configured boundary transfer. Summary/conservation serialize available, supplied, consumed, residual and stoichiometric cap; CO/VOC/NOx remain `not_evaluated`. | `models/common.py`, `models/l0.py`, `models/l1.py` | `test_organic_oxidation_is_bounded_by_finite_oxygen_inventory_and_flux` |
| B3 current-pore molar Fick transport | Every gas integrates conservative `mol/m3_reference_bulk` state with explicit species `kg/mol`; current-pore `mol/m3` drives isotropic deforming Fick/surface flux before exact mass mapping. Artifacts expose mass↔moles↔current-pore conversion. | `models/fvm.py`, `models/common.py`, `models/l1.py`, `models/l0.py` | H2O/CO2 different-molar-mass manufactured tests; `test_current_pore_molar_fick_flux_uses_phi_and_deforming_geometry_conservatively`; low-gradient agreement |
| B4 fail-safe robust UQ | Every policy sample retains index/fixed status plus deterministic sample ID, seed/algorithm, parameters, case/parameter-pack hashes and forward primary-state hash; arbitrary solver messages are not persisted. The default/configured maximum failure rate is zero; required-sample failure makes the record infeasible and excludes it from robust Pareto. | `inverse/search.py`, `validation.py` | `test_inverse_required_policy_sample_failures_are_fail_safe_and_auditable` (1/4, 3/4, 4/4 failures); policy provenance/hash test |
| B5 validation/structured failure | Type-safe loader leaves malformed top-level/kiln/profile/inverse containers to validation (exit 2/no traceback). Forward L0/L1, inverse and benchmark runtime exceptions atomically write only fixed stage/reason and exact-built-in allowlist category; exception string/repr/args/traceback/locals, real class name, resolved input, CLI args and paths never enter durable output or stdout/stderr. Occupied outputs are preserved in a sibling failure lane. `KeyboardInterrupt`/`SystemExit` are not caught. | `config.py`, `validation.py`, `cli.py`, `io/artifacts.py` | five runtime lanes × credential/PII-shaped sentinel matrix; custom exception class; recursive output scan; malformed/process-control/atomic regressions |
| B6 thermo honesty | Forward invokes `MinimalGibbsBackend` and records source hash/backend status. Composition mapping coverage responds to phase/oxide changes, but absent oxide-liquid Gibbs data keeps status `not_evaluated_*`, marks liquid as an unresolved proxy and forbids thermo hard-pass. | `thermo/coverage.py`, `models/common.py`, `inverse/constraints.py` | `test_thermo_coverage_is_traceable_composition_sensitive_and_never_fake_hard_pass` |
| B7 enthalpy honesty | The former same-source metric is renamed end-to-end to `reduced_effective_enthalpy_ode_*`; complete physical energy conservation is `not_evaluated` and excluded from hard-pass. Coverage lists omitted variable-mass/gas sensible-enthalpy terms. Wet-feed and forming water remain in the reduced model. | `models/common.py`, `inverse/constraints.py`, `io/artifacts.py`, `cli.py` | `test_reduced_enthalpy_ode_residual_is_not_mislabeled_full_energy_conservation`; `test_l0_matches_manufactured_newton_cooling_limit`; `test_forward_accepts_and_records_tightened_solver_tolerances` |
| B8 independent semantics | SHA-256/size remains byte integrity only. Forward contract 5.0 binds case/fidelity/parameter/source/solver provenance and strict mode independently reruns the L0/L1 ODE/FVM solver. A trusted versioned range admits only finite numeric solver rtol/atol, while independent verifier-owned `rtol=5e-6`/`atol=5e-8` hard caps control semantic acceptance. Replay primary temperature/extents/species inventories/volume/porosity/heat states are compared point-by-point before replay-derived pressure/liquid/stress/summary/extrema/conservation/CSV; algebraic self-consistency and endpoint enthalpy identity cannot substitute. Forward seed is integrity-only because the deterministic solver does not consume it: missing/one-sided changes fail but coherent rewrite is not claimed detectable without external authenticity. Explicit custom fixtures are `not_evaluated`/integrity-only. Tiny/default inverse seed replay remains unchanged. | `io/artifacts.py`, `models/common.py`, `inverse/search.py` | coherent rehashed +10 K temperature and molar-inventory attacks under default/invalid tolerances; finite/range policy; machine-roundoff/mapping-order controls; missing/one-sided/coherent forward seed contract; original L0/L1 plus inverse replay; prior schema/summary/Pareto matrix |

## Additional honesty/operational fixes

- Fewer than three paired L0/L1 points return `insufficient_points`; two-point ranges are `observed_candidate_envelope`, never a continuously validated window.
- Active constraints are defined by serialized normalized slack (`slack <= 0.05`).
- Nonempty output directories are rejected unless `--overwrite`; explicit overwrite retains a rollback sibling and commits a sibling temporary directory by atomic rename.
- Newton-cooling, nontrivial deforming Fick, low-gradient L0/L1, tightened-tolerance, malformed-boundary, partial-UQ and semantic tamper paths are automated tests.

## Verification results — second rework / round 3

Fresh frozen environment: `UV_PROJECT_ENVIRONMENT=.venv-round3 .tools/uv sync --frozen --extra dev` installed 8 pinned packages; `.tools/uv pip check --python .venv-round3/bin/python` reported all packages compatible. `.venv-round3/bin/python -m compileall -q src tests scripts` returned exit 0. Final `.venv-round3/bin/python -m pytest -q` returned **87 passed in 858.16 s** (14:18.80 wall, max RSS 128,280 KiB), increased from the round-2 baseline of 63 tests.

Fresh artifacts are under `runs/safety_review_round3/`:

- validate: exit 0, `valid=true`, source coverage 1.0;
- L0 + strict verify: exit 0/0; mass `3.572903404209115e-11`, element `1.2310248741826218e-10`, reduced ODE enthalpy `2.306315477387857e-15`; every independent semantic/hash/CSV/count check true; 1.76 s wall, 96,856 KiB max RSS;
- L1 + strict verify: exit 0/0; mass `2.079573997986371e-11`, element `5.5631257862421855e-11`, reduced ODE enthalpy `1.4914998709531423e-15`; 21/41 converged and every independent semantic/hash/CSV/count check true; 102.25 s wall, 112,168 KiB max RSS;
- inverse + strict verify: exit 0/0; 16 L0 designs, 18 records, 16 L0 feasible, 2 L1 ranked and 2 Pareto; independently recomputed constraints/counts/nondominance/source hashes/Pareto CSV/rank/envelope all true; 331.05 s wall, 121,084 KiB max RSS;
- benchmark: L0 `0.6065 s`; L1 including 21/41 `102.9711 s`; peak RSS `109,981,696 bytes`; `workers=1`, `within_budget=true`; outer process 104.65 s wall and 110,064 KiB max RSS.

`scripts/round3_hostile_probes.py` generated `hostile_probe_results.json`. All six malformed top-level/kiln/profile/inverse cases exited 2 with structured validation and no traceback. Injected forward L0/L1, inverse and benchmark RuntimeErrors all exited 3 with atomic status/provenance/manifest and no traceback. Untampered forward/inverse originals remained strict-valid. Every synchronized-hash attack was rejected: positive density×2, legal-range summary change, zeroed mass/element/O2/reduced-enthalpy residuals, trajectory count/CSV changes, inverse summary count, constraint/source/rank/envelope/Pareto CSV changes and traceable-but-wrong Pareto replacement. The narrowly filtered SciPy sparse-Jacobian warning path is covered by a no-`RuntimeWarning` regression; finite state, conservation, bounds and solver status remain mandatory.

The authoritative acceptance condition remains each actual command exit code and serialized checks. No synthetic output is a production validation.

## Verification results — third rework / round 4

The first cross-process replay attempt showed that an exact full-state digest was not deterministic: semantically equivalent resolved-case mapping order changed thermo missing-phase list order and machine-roundoff values. That assumption did not hold. The final contract hashes primary state plus only semantic provenance, normalizes finite floats to 8 significant digits, and has RED→GREEN tests for solver roundoff, material change and equivalent mapping order. A fresh independent-process replay then passed.

Fresh frozen environment: `UV_PROJECT_ENVIRONMENT=.venv-safety-review4 .tools/uv sync --frozen --extra dev` installed 8 pinned packages; `uv pip check` reported all compatible; `compileall -q src tests scripts` exited 0. Collection increased from 87 to **118 tests**. Final full `.venv-safety-review4/bin/python -m pytest -q` returned **118 passed in 1175.81 s** (19:36.49 wall, 131,780 KiB max RSS).

Fresh artifacts are under `runs/safety_review_round4/`:

- L0 run/strict: exit 0/0; run 1.55 s and 97,188 KiB; strict 0.95 s and 96,384 KiB.
- L1 run/strict: exit 0/0; 21/41 converged; run 1:43.88 and 112,520 KiB; strict 1.04 s and 100,700 KiB.
- inverse run: exit 0; 16 L0, 18 total records, 16 L0 feasible, 2 L1 ranked, 2 Pareto; 5:58.79 and 121,444 KiB.
- inverse strict replay in a fresh process: exit 0; `inverse_deterministic_replay`, ordered-record and Pareto replay checks true; 5:59.78 and 122,048 KiB.
- benchmark: exit 0; L0 0.804 s, L1 including grid check 101.446 s; outer 1:43.50 and 112,684 KiB; workers=1, within_budget=true; both child strict checks passed.
- B1–B7/B3 regression file: 62 passed in 47.09 s; focused H2O/CO2 molar-current-pore suite: 4 passed.
- `scripts/round4_hostile_probes.py`: five credential/class sentinel failure lanes secure; untampered forward/inverse strict-valid; all 10 forward schema/full-trajectory/summary attacks and all 7 inverse add/delete/reorder/source/Pareto-decision/constraint/nondominance attacks rejected. Matrix exit 0 in 6:04.13, 119,936 KiB.

No OCI, network solver, paid API, external publish/send, PLC/robot/kiln connection or production-control action was used. SHA-256 integrity, semantic replay and absent cryptographic authenticity are separated in `VERIFIER_THREAT_MODEL.md`.

## Verification results — fourth rework / round 5

The round-4 coherent attack reproduced first: an interior L0 temperature was raised by 10 K, dependent heat/pressure/liquid/stress/CSV fields and manifest hashes were updated, and old strict verification returned exit 0. The new RED test observed that exact false acceptance. A first fresh-process L1 replay then exposed a separate assumption: `{}` parameter provenance was treated as equivalent to the original `None` invocation, which silently omitted the 21/41 grid replay. That assumption did not hold. Provenance now distinguishes `model_defaults` from `explicit_overrides`; the final fresh L1 run and independent strict replay both execute the 21/41 path.

Fresh frozen environment: `UV_PROJECT_ENVIRONMENT=.venv-round5 .tools/uv sync --frozen --extra dev` installed 8 pinned packages; `uv pip check` reported all packages compatible; `compileall -q src tests scripts` exited 0. Collection increased from 118 to **130 tests**. Final `.venv-round5/bin/python -m pytest -q` returned **130 passed in 1500.08 s** (25:00.70 wall, 129,852 KiB max RSS).

Fresh artifacts and timing evidence are under `runs/safety_review_round5/`:

- L0 run/strict replay: exit 0/0; 1.66 s / 1.55 s wall; 97,244 / 97,068 KiB max RSS; every forward replay provenance, solver-statistics, primary-state, derived-state, summary/conservation and CSV check is true.
- L1 21/41 run/strict replay: exit 0/0; 1:42.94 / 1:42.37 wall; 109,128 / 116,772 KiB max RSS; `forward_semantic_replay=true` and all pointwise primary/derived checks are true.
- inverse run/fresh strict replay: exit 0/0; 16 L0 designs, 18 records, 16 L0 feasible, 2 L1 ranked and 2 Pareto; 5:33.75 / 5:32.65 wall; 120,216 / 122,168 KiB max RSS; deterministic replay and all ordered-record/Pareto checks are true.
- benchmark: exit 0, 1:42.63 wall, 112,720 KiB max RSS, `workers=1`, `within_budget=true`; L0 solver wall 0.7446 s and L1 solver wall 17.9458 s within the 100.8123 s L1 21/41 benchmark record. Both child strict replays passed; L1 strict took 1:42.87 and 115,400 KiB.
- Round-4 credential/forward/inverse independent hostile driver rerun against round-5 artifacts: exit 0 in 5:42.28, 125,352 KiB. All seven acceptance booleans are true, including `unreplayed_primary_temperature_rejected`; five credential lanes, prior forward attacks and all inverse attacks remained secure.
- New hostile controls reject coherent temperature and molar-inventory changes, missing replay descriptor, parameter/source/solver version/configuration/statistics tampering and malformed software provenance; mapping-order changes and machine-roundoff-scale temperature changes pass. Explicit manufactured/custom opt-out is labeled `not_evaluated`, moves the ODE trajectory to integrity-only and makes strict return nonzero.
- B1–B7 regression: 62 passed in 59.23 s. Focused B3 molar/current-pore suite: 4 passed in 16.87 s.

No signature, MAC, attestation or protected timestamp was added. An attacker able to replace the verifier, dependencies and all states remains outside the threat boundary. No OCI, network solver, paid API, external publish/send, PLC/robot/kiln connection or production-control action was used.
