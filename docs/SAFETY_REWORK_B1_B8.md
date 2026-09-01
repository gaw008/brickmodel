# Safety rework B1–B8 evidence map

Scope: research-only synthetic MVP. This document does not approve production recipes, emissions/compliance claims, kiln-speed control or any PLC/robot/kiln connection.

## Code and regression-test map

| Finding | Implemented behavior | Primary code | Regression evidence |
|---|---|---|---|
| B1 phantom dimensions | Wet-feed water enters wet mass/effective heat capacity and reaction potential; PSD/morphology enter permeability and transfer; oxide chemistry enters an explicitly unresolved liquid screening proxy; feed density/cp/k/effective gas diffusivity are mixed into the forward model. The inverse transform has exactly 12 physically coupled coordinates. | `models/common.py`, `chemistry/stoichiometry.py`, `inverse/transforms.py` | `test_feed_moisture_morphology_and_oxide_fingerprint_are_not_phantom`; `test_every_inverse_coordinate_changes_an_interpretable_physical_quantity` |
| B2 oxygen-limited chemistry | Organic oxidation uses zero multiplier at zero O2 and is capped by initial pore O2 plus the time-integral of configured boundary transfer. Summary/conservation serialize available, supplied, consumed, residual and stoichiometric cap; CO/VOC/NOx remain `not_evaluated`. | `models/common.py`, `models/l0.py`, `models/l1.py` | `test_organic_oxidation_is_bounded_by_finite_oxygen_inventory_and_flux` |
| B3 current-pore Fick transport | Conservative storage remains per reference bulk volume, while flux uses `c_current=N_ref/(phi_open J)`, isotropic deforming geometry and current-surface transfer. | `models/fvm.py`, `models/l1.py`, `models/l0.py` | `test_current_pore_fick_flux_uses_phi_and_deforming_geometry_conservatively`; `test_l1_serializes_current_pore_concentration_and_agrees_with_l0_at_low_gradient` |
| B4 fail-safe robust UQ | Every policy sample retains index/status/message. The default/configured maximum failure rate is zero; required-sample failure makes the record infeasible and excludes it from robust Pareto. A nonzero policy requires explicit scientific basis validation. | `inverse/search.py`, `validation.py` | `test_inverse_required_policy_sample_failures_are_fail_safe_and_auditable` (1/4, 3/4, 4/4 failures) |
| B5 validation/structured failure | Cross-field, finite, positivity, bounds and count invariants are validated before solving. Forward solver exceptions create a structured failed run and CLI exit 3 without traceback. | `validation.py`, `cli.py`, `io/artifacts.py` | `test_validator_rejects_cross_field_and_positive_invariant_mutations`; `test_invalid_schema_cli_validate_returns_exit_2_without_solver_traceback`; `test_solver_exception_writes_structured_failure_artifact_and_returns_exit_3` |
| B6 thermo honesty | Forward invokes `MinimalGibbsBackend` and records source hash/backend status. Composition mapping coverage responds to phase/oxide changes, but absent oxide-liquid Gibbs data keeps status `not_evaluated_*`, marks liquid as an unresolved proxy and forbids thermo hard-pass. | `thermo/coverage.py`, `models/common.py`, `inverse/constraints.py` | `test_thermo_coverage_is_traceable_composition_sensitive_and_never_fake_hard_pass` |
| B7 enthalpy honesty | The former same-source metric is renamed end-to-end to `reduced_effective_enthalpy_ode_*`; complete physical energy conservation is `not_evaluated` and excluded from hard-pass. Coverage lists omitted variable-mass/gas sensible-enthalpy terms. Wet-feed and forming water remain in the reduced model. | `models/common.py`, `inverse/constraints.py`, `io/artifacts.py`, `cli.py` | `test_reduced_enthalpy_ode_residual_is_not_mislabeled_full_energy_conservation`; `test_l0_matches_manufactured_newton_cooling_limit`; `test_forward_accepts_and_records_tightened_solver_tolerances` |
| B8 tamper-evident semantics | Manifest records SHA-256 and size for every non-manifest payload (self-hash impossibility is explicit). Strict verify checks inventory exactness, hashes/sizes, finite/state bounds, density, summary/trajectory consistency, conservation, exact Pareto-record traceability and nondominance. | `io/artifacts.py` | `test_manifest_hashes_every_payload_and_strict_verify_rejects_hash_and_semantic_tampering`; `test_strict_verify_rejects_rehashed_negative_gas_state`; `test_strict_verify_returns_structured_invalid_for_scalar_trajectory_state`; `test_inverse_traceability_requires_exact_pareto_record_match` |

## Additional honesty/operational fixes

- Fewer than three paired L0/L1 points return `insufficient_points`; two-point ranges are `observed_candidate_envelope`, never a continuously validated window.
- Active constraints are defined by serialized normalized slack (`slack <= 0.05`).
- Nonempty output directories are rejected unless `--overwrite`; explicit overwrite retains a rollback sibling and commits a sibling temporary directory by atomic rename.
- Newton-cooling, nontrivial deforming Fick, low-gradient L0/L1, tightened-tolerance, malformed-boundary, partial-UQ and semantic tamper paths are automated tests.

## Verification results

Frozen environment: `UV_PROJECT_ENVIRONMENT=.venv-rework .tools/uv sync --frozen --extra dev` installed 8 packages; `.tools/uv pip check --python .venv-rework/bin/python` reported all packages compatible. `python -m compileall -q src tests` returned exit 0. Final `pytest -q` returned **63 passed in 641.27 s**, versus the reviewed baseline of 25 tests.

Fresh artifacts are under `runs/review_rework_final_20260901/`:

- validate: exit 0, `valid=true`, source coverage 1.0;
- L0 + strict verify: exit 0/0; mass `3.812819550424689e-12`, element `1.313716057318795e-11`, reduced ODE enthalpy `6.037671410982674e-15`, semantic/hash checks all true;
- L1 + strict verify: exit 0/0; mass `3.7015663446887777e-13`, element `4.931597958926337e-11`, reduced ODE enthalpy `5.678885758766502e-14`, 21/41 grid converged and semantic/hash checks all true;
- inverse + strict verify: exit 0/0; 16 L0 designs, 18 total records, 16 L0 feasible, 2 L1 ranked, 2 exact-traceable Pareto; two-point rank status `insufficient_points`;
- benchmark: L0 `0.6124 s`; L1 including 21/41 `87.1361 s`; peak RSS `111,157,248 bytes`; `within_budget=true` on one worker.

Re-run probes returned: moisture/sphericity/100% Fe2O3 selected fingerprints are no longer exactly equal to baseline; zero-O2 organic completion is `0.0`; manufactured 1-success+3-failure UQ is `infeasible/all_hard_constraints=false`; invalid forming moisture exits 2; 15 selected zero-O2/phantom/UQ/schema/thermo/tamper tests pass. The inverse CLI emitted SciPy numerical-Jacobian overflow/invalid `RuntimeWarning`s for some sampled L1 solves while all structured solver, conservation, state-bound and 21/41 checks still passed; this warning is retained as residual numerical risk rather than suppressed.

The authoritative acceptance condition remains each actual command exit code and serialized checks. No synthetic output is a production validation.
