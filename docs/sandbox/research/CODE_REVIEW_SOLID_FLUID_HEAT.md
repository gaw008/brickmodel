# Independent review: solid/fluid transport host and water-transfer adaptation

Scope: `solid_fluid_heat.py`, the `water_phase_transfer.py` host adaptation, their new tests and `SOLID_FLUID_HEAT.md`. The reviewer inspected complete host code, the wrapper diff, the underlying storage API and the reused face/enthalpy helpers. No implementation was edited by the reviewer.

## Assembly and identity audit

`InventoryLayout` requires complete, disjoint named liquid/gas/solid columns and supports arbitrary explicit order. Every extraction and face/source placement uses the layout, so a leading solid or middle liquid column is not mistaken for gas. The bare `ConservedState` has no layout metadata: equal-shape arrays with silently permuted caller meanings cannot be automatically detected. The final documentation correctly states this caller contract rather than claiming a nonexistent restart/hash validator.

Each solid/fluid storage is bound to the corresponding exact transport-template object, retaining water/caloric/policy/envelope identity. Geometry is checked against area times width within a stated two-ULP representation tolerance. Actual per-trial decoding uses the complete solid inventory and whole-cell U through `SolidFluidStorage`; it does not use the template's old pore volume or old fluid-only inverse. The resulting gas state uses the actual remaining gas volume and current T, and retains the new complete inverse/state diagnostics.

Reuse is confined to configured face transport, same-source gas enthalpy and conduction formulas. Each internal face is assembled once in mol/s and W, shared with opposite signs. Liquid and solid face columns remain zero. Both diffusive and advective species enthalpies come from the fully bound gas curves, with the existing common-face/donor-temperature conventions. Solid thermal energy changes temperature through the overall inverse; it is not inserted again as a face energy term.

The water wrapper explicitly supports both host types, uses the new layout's liquid index and the named gas H2O column, and preserves the existing real-liquid/ideal-water chemical reference checks. Its source moves equal water mol amounts between phases, keeps solid/carrier inventories fixed and introduces no duplicate latent heat or pressure work. The old host's index and result behavior remain supported.

## Findings corrected during review

The first adaptation's manufactured-mode test considered kinetic/transport/gas classifications but omitted new solid and geometry classifications. Inspection identified that a host with otherwise nonmanufactured classifications and a manufactured solid could therefore bypass the wrapper's own opt-in. The final code explicitly includes solid and geometry classifications. The reviewer independently constructed a classification-control fixture with only the solid remaining manufactured and observed `manufactured_requires_explicit_test_mode`. This probe tests classification enforcement; relabelled fixture coefficients are not asserted to become real literature evidence.

The new solid-domain exceptions require explicit mapping before falling back to the original fluid failure classifier. The final helper maps actual solid temperature/pressure and no-positive-fluid-volume exits to DomainExit, while uncertainty-budget failures remain numerical contract failures. An independent probe queried 300 K inside the fluid domain with an active solid restricted to 301–500 K and observed `solid_temperature_out_of_domain` as DomainExit. The permanent test was likewise strengthened because its earlier 289 K input would have exercised the fluid's earlier temperature gate instead.

## Executed tests and exact snapshot distinction

The initial collected suite combined the 13 new cases with 16 unchanged old water-transfer cases:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_solid_fluid_heat.py tests/sandbox/test_solid_water_phase_transfer.py tests/sandbox/test_water_phase_transfer.py -q --junitxml=/private/tmp/solid-fluid-heat-review.xml
```

Result: **29 passed in 54.68 s**. XML SHA-256: `fbae224ae260cc2f2a86fb5ea026a5ff6d8727cabbfb9dad7d8a1a0a31a90f57`.

During that run, the implementer strengthened the already-collected tests without changing source: the existing two-Cp evaporation trajectories now compare final temperature *error intervals*, and the solid-domain case isolates the solid domain. The original XML is therefore not represented as execution of those later assertions. After it finished, the reviewer ran only the two changed numerical/domain cases:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_solid_water_phase_transfer.py::test_real_solid_water_phase_transfer_conserves_and_responds_to_solid_cp tests/sandbox/test_solid_fluid_heat.py::test_solid_domain_exit_is_preserved -q --junitxml=/private/tmp/solid-fluid-heat-strengthened-review.xml
```

Result: **2 passed in 17.37 s**. XML SHA-256: `c05b3b9db0eddfa3bce7b9af72bc67edc9d00739e3d1d5d7982ae5bdaafa2fe5`. The renamed whole-host manufactured test did not change its assertions; the independent solid-only probe above supplements that test's broader coverage.

The actual two-cell integration conserves complete species totals and U with immobile liquid/solid columns. The actual one-cell water-transfer runs at solid Cp 10 and 100 J/mol/K preserve water, carrier, solid and energy inventories. The strengthened check requires the low-Cp final temperature interval to lie strictly below the high-Cp interval, and the high-Cp upper bound to remain below 300 K. Thus the observed thermal moderation is resolved under the current conditional numerical budget, not merely a difference in rounded nominal temperatures. These remain short manufactured-coefficient examples, not space/time convergence or real material calibration.

## Final source and test SHA-256 binding

The source hashes below apply to both reviewer runs; the new test hashes identify the strengthened final files, whose changed assertions were separately executed as described above.

| File | SHA-256 |
|---|---|
| `src/sludge_sandbox/solid_fluid_heat.py` | `1edd7d7bf4dec9cfee0c4b36ea4eacb4495fe02832d0ce5575f0b55344d0390d` |
| `src/sludge_sandbox/water_phase_transfer.py` | `3e8bfa50c0361ca7287994bce98c36307c34ceedff22082c2f631f3accc409fc` |
| `tests/sandbox/test_solid_fluid_heat.py` | `378312b689211abdba83c3b154502c6309283d43732df9f05602adcfbdac2c0c` |
| `tests/sandbox/test_solid_water_phase_transfer.py` | `91a2cd0550f7eb5ef88fabdf5715d5df8b56fd0ca9cdaa3de193c5ceebbe3246` |
| `tests/sandbox/test_water_phase_transfer.py` | `0499cbd72644889a6a1f76d25b466ea8dcdd1db4b80aa6db9fd29882e93f12b1` |
| `docs/sandbox/SOLID_FLUID_HEAT.md` | `7db10597100ee72f454e79ca9ea0754aeab537a466ccb36d416fc2185a01c643` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass; manufactured-gate omission corrected |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — fixed inert-solid storage is actually coupled to shared fluid/heat faces and the existing-interface water-transfer model. Missing reactions, solid transitions, drying constitutive data, shrinkage and full brick-model qualification are not waived by this bounded approval.
