# Parameter source and validity table

Machine-readable normative table: `data/parameter_pack_synthetic_v1.json`. Every entry carries default, interval (or enthalpy interval), unit, `source_kind` and validity. Defaults are executable assumptions, not measured plant values.

| Parameter | Default | Unit | Source kind | Validity / limitation |
|---|---:|---|---|---|
| solid specific heat | 1000 | J/kg/K | synthetic policy | effective 300–1500 K mixture |
| solid thermal conductivity | 1.0 | W/m/K | public effective-medium closure ensemble | porous fired-clay screening; morphology uncertain |
| gas effective diffusivity | 1e-7 | m2/s | synthetic policy | open-pore proxy |
| emissivity | 0.8 | 1 | synthetic policy | gray opaque surface |
| true solid density | 2600 | kg/m3 | synthetic policy | silicate-rich synthetic mixture |
| open-pore connectivity | 0.7 | 1 | model-form unknown | not measured connectivity |
| dense-strength proxy | 5e7 | Pa | empirical proxy unknown | never certification strength |
| strength/porosity coefficient | 5.0 | 1 | empirical proxy unknown | never certification strength |
| bloating pressure scale | 4.5e8 | Pa | defect proxy unknown | configured synthetic normalization, not failure threshold |
| Kozeny–Carman constant | 180 | 1 | semi-empirical closure | material/morphology dependent |
| free-water `A,E` | 2e4, 6e4 | 1/s, J/mol | public property + synthetic kinetics | effective evaporation step |
| free-water enthalpy | 2.26e6 | J/kg product | public property interval | phase-change approximation |
| organic `A,E` | 1e6, 1e5 | 1/s, J/mol | sludge-pyrolysis literature window + synthetic policy | pseudo-component only |
| organic enthalpy | -1e7 | J/kg feed | synthetic interval | unknown feed LHV/reaction partition |
| kaolinite `A,E` | 2e6, 1.5e5 | 1/s, J/mol | kaolinite literature window + synthetic policy | pseudo-phase |
| kaolinite gas enthalpy | 3e6 | J/kg product | synthetic interval | non-zero unknown assumption |
| calcite `A,E` | 5e6, 1.8e5 | 1/s, J/mol | synthetic policy | pseudo-step |
| calcite gas enthalpy | 4e6 | J/kg product | synthetic interval | non-zero unknown assumption |
| sintering rate at 1273 K | 2e-6 | 1/s | SOVS-inspired synthetic closure | reduced isotropic screening |
| sintering activation energy | 1.2e5 | J/mol | material-specific unknown | interval, not calibrated |

Public links and exact validity statements are in `data/sources.json`. Planner's 23-source rationale remains under `docs/planner/sludge_brick_first_principles_report.md`.

## Unknown handling

- Complete multicomponent oxide-liquid/glass thermodynamics: missing; pseudo-liquid coverage flag is mandatory.
- Real matrix fingerprint, kinetics, transport, SOVS, stress, strength and connectivity: unknown intervals/closures.
- Real kiln map and equipment-approved speed bounds: absent; synthetic fixed map only.
- Product/environmental limits: absent; environmental result is `not_evaluated`.
- Missing VOC/toxic species never means zero emissions.

Policy intervals are not called empirical probability distributions. `uq` sampling is an exploration policy, and model-form discrepancy is reported separately.
