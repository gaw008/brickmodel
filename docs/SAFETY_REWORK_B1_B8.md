# Safety rework B1–B8 evidence map

Scope: research-only synthetic MVP. This document does not approve production recipes, emissions/compliance claims, kiln-speed control or any PLC/robot/kiln connection.

## Code and regression-test map

| Finding | Implemented behavior | Primary code | Regression evidence |
|---|---|---|---|
| B1 phantom dimensions | Wet-feed water enters wet mass/effective heat capacity and reaction potential; PSD/morphology enter permeability and transfer; oxide chemistry enters an explicitly unresolved liquid screening proxy; feed density/cp/k/effective gas diffusivity are mixed into the forward model. The inverse transform has exactly 12 physically coupled coordinates. | `models/common.py`, `chemistry/stoichiometry.py`, `inverse/transforms.py` | `test_feed_moisture_morphology_and_oxide_fingerprint_are_not_phantom`; `test_every_inverse_coordinate_changes_an_interpretable_physical_quantity` |
| B2 oxygen-limited chemistry | Organic oxidation uses zero multiplier at zero O2 and is capped by initial pore O2 plus the time-integral of configured boundary transfer. Summary/conservation serialize available, supplied, consumed, residual and stoichiometric cap; CO/VOC/NOx remain `not_evaluated`. | `models/common.py`, `models/l0.py`, `models/l1.py` | `test_organic_oxidation_is_bounded_by_finite_oxygen_inventory_and_flux` |
| B3 current-pore molar Fick transport | Every gas integrates conservative `mol/m3_reference_bulk` state with explicit species `kg/mol`; current-pore `mol/m3` drives isotropic deforming Fick/surface flux before exact mass mapping. Artifacts expose mass↔moles↔current-pore conversion. | `models/fvm.py`, `models/common.py`, `models/l1.py`, `models/l0.py` | H2O/CO2 different-molar-mass manufactured tests; `test_current_pore_molar_fick_flux_uses_phi_and_deforming_geometry_conservatively`; low-gradient agreement |
| B4 fail-safe robust UQ | Every policy sample retains index/status/message. The default/configured maximum failure rate is zero; required-sample failure makes the record infeasible and excludes it from robust Pareto. A nonzero policy requires explicit scientific basis validation. | `inverse/search.py`, `validation.py` | `test_inverse_required_policy_sample_failures_are_fail_safe_and_auditable` (1/4, 3/4, 4/4 failures) |
| B5 validation/structured failure | Type-safe loader leaves malformed top-level/kiln/profile/inverse containers to validation (exit 2/no traceback). Forward L0/L1, inverse and benchmark runtime exceptions atomically write stage/reason/safe-exception/provenance/manifest artifacts and exit 3; occupied outputs are preserved in a sibling failure lane. `KeyboardInterrupt`/`SystemExit` are not caught. | `config.py`, `validation.py`, `cli.py`, `io/artifacts.py` | malformed-container matrix; injected L0/L1/inverse/benchmark exceptions; nonempty-output preservation tests |
| B6 thermo honesty | Forward invokes `MinimalGibbsBackend` and records source hash/backend status. Composition mapping coverage responds to phase/oxide changes, but absent oxide-liquid Gibbs data keeps status `not_evaluated_*`, marks liquid as an unresolved proxy and forbids thermo hard-pass. | `thermo/coverage.py`, `models/common.py`, `inverse/constraints.py` | `test_thermo_coverage_is_traceable_composition_sensitive_and_never_fake_hard_pass` |
| B7 enthalpy honesty | The former same-source metric is renamed end-to-end to `reduced_effective_enthalpy_ode_*`; complete physical energy conservation is `not_evaluated` and excluded from hard-pass. Coverage lists omitted variable-mass/gas sensible-enthalpy terms. Wet-feed and forming water remain in the reduced model. | `models/common.py`, `inverse/constraints.py`, `io/artifacts.py`, `cli.py` | `test_reduced_enthalpy_ode_residual_is_not_mislabeled_full_energy_conservation`; `test_l0_matches_manufactured_newton_cooling_limit`; `test_forward_accepts_and_records_tightened_solver_tolerances` |
| B8 independent semantics | SHA-256/size remains byte integrity only. Forward strict verify rebuilds context from resolved case/provenance and independently recomputes trajectory-derived fields, all summary values/status, mass/bulk-volume/element/O2/reduced-enthalpy ledgers and counts from schema-2.0 extensive states. Inverse recomputes sample quantiles, constraints/slacks/objectives/counts, nondominance against all L1 hard-feasible records, Pareto JSON/CSV traceability and envelope sources. | `io/artifacts.py`, `models/common.py`, `inverse/search.py` | rehashed legal density/summary, zeroed residual/O2/enthalpy, count, constraint, source, CSV, envelope and dominated-Pareto hostile tests; originals remain strict-valid |

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
