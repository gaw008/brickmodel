# Shared spherical convection and radiation boundary

The implementation extends the existing ProgrammedSolidFluidHeat._surface path to use the selected transport's physical outer area and shared half-cell conduction helper. This retains current-geometry transport for moving slabs. No new PDE, material constants, surface root solver or numerical acceptance threshold is introduced.

## Physical scope

For outer radius R and last midpoint rc, G=4πk/(1/rc−1/R). The surface balance is G(Ts−Tc)=4πR²[h(Tg−Ts)+εσ(Trad⁴−Ts⁴)]. Conductive inward power enters the existing outward face energy ledger with negative sign. Gas donor enthalpy remains separately assembled. Gray radiation uses the existing effective blackbody environment assumption, not an inferred Nylen wall temperature. Geometric derivation and limits are in ../../RADIAL_HEAT_GEOMETRY.md.

## Recorded development

A real initial test failed because the previous constructor rejected spherical programmed boundaries; the source and RED log are preserved. Minimal shared-helper wiring then passed the actual linear film case. The first complete new test run passed eight cases but the multi-cell Robin case returned resource_limit/wall_time_limit under its 30-second per-grid budget. The run terminated with 1 failed, 8 passed in 70.45 seconds. This is a resource failure, not a measured error-bound failure.

Based on that actual cost, only the Robin per-grid wall budget was increased to 90 seconds. Geometry, physical inputs, Fourier time .05, 4/8/16 meshes, .001/.0005-second step caps and all error gates remained fixed. Subsequent per-grid metrics must report terminal status and time, including any failure. The original failed log remains part of this record.

## Verification targets

Actual one-cell film surface temperature and heat, nonlinear radiation against an independent root, heating/ramp/cooling at explicit knots versus analytic constant-capacity evolution, local step energy closure, zero-k boundary limits with separate gas enthalpy, and failed surface-root propagation. Multi-cell Bi=1 Robin mode uses μ=π/2 in the same SolidFluidHeat and integrate path; geometric and temporal errors are separately checked. All caloric/transport constants here are manufactured numerical fixtures.

Final source and independent results are recorded below. Old sphere-program rejection is replaced by positive physical verification; moving-sphere and radial-liquid restrictions remain.

## Scientific limits and next work

This enables a necessary heat boundary for spherical public experiments. It does not provide MSJ/CB material heat capacity, conductivity, moisture transport, emissivity, hot-stream humidity or shrinking-radius history. It does not reinterpret the first radial midpoint as a center thermocouple. Full raw-sludge material qualification, wet/firing/cooling integration, three public mechanism validations, multi-generation search and application acceptance remain required by the original Goal.


## Completed surface validation

Frozen source run: 19 passed in 79.04 seconds, terminal process 65244. Four Robin RMS errors: 0.013373991603524484, 0.0033048247957516612, 0.0008154527384661139, 0.0008154412764939201 K. Finest time-halving maximum difference 1.645332758926088e-8 K. Accepted steps 107/107/107/214; zero rejections; every run reached Fourier time .05 within its recorded resource budget. Independent review checked the governing mode, capacity and all saved metrics/gates, without repeating the four runs. Raw final temperature vectors were not exported, so the review does not claim an independent RMS reconstruction from archived states.

Independent implementation checks: 28 prior-HEAD slab golden records bit-identical; 3 separate high-precision radiation/current-geometry/zero-k donor-enthalpy checks passed. One existing FreeSolidSlab current-surface regression passed; a prescribed-deformation regression failed before surface evaluation because its CurrentSlab cache contains arrays unsupported by existing identity encoding. The prior HEAD wrapper reproduces this same failure. This is an outstanding existing software defect, not hidden by the spherical results; the precise path and required repair are saved here.

Noneditable installed test selection (new surface cases except the already completed multi-grid run, existing programmed/slab and wrapper tests) initially produced 29 passed, 2 failed, 1 deselected in 9.89 seconds. Both failures were old constructor-bypassing test doubles rejected by the existing configuration check; the prior wrapper reproduces both failures. They were replaced with a real admitted manufactured host, preserving identity, actual surface and gas-flow calculations, while instrumenting only a 3 W power component. All four wrapper tests then passed in 1.12 seconds against the same installed source. Both original XML and corrected-test XML are retained; no aggregate full-suite PASS is claimed. Final installation byte-matched 107 modules. The expensive multi-grid result is attributed to source execution, not an installed rerun.
