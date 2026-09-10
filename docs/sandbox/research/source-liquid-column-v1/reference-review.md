# Source liquid-column independent numerical review

The predeclared manufactured-liquid experiment passed within its 45 s hard limit (25.55175 s actual). No conditions, convergence gates or tolerances were changed after execution. There was no failed trajectory in this experiment to discard. The script, actual stdout and values are check_liquid.py, ORACLE.log and RESULT.json. ORACLE_PLAN.md records the pre-run choices.

## Frozen implementation and physical assembly

The run-pinned source_wet_column.py, liquid_transport_state.py and test_source_liquid_column.py hashes exactly match `/private/tmp/brick-source-liquid-column-v1/FREEZE.json`. All six current freeze file hashes were separately checked after the run; FREEZE_BINDING.json stores that comparison and the original freeze contents/SHA. The closed oracle directly exercised the source-column/helper path, not the programmed boundary wrapper or old solid host, so current hash matching is not presented as independent execution of those other paths.

Reviewed implementation uses SourceWetPoint.pressure_error_pa, including the available-volume contribution, to form decoded liquid state at the same inverse T/P. Planar liquid total pressure, not vapor partial pressure, drives the liquid face. Saturation is liquid volume divided by available liquid-plus-gas volume. The helper and returned rates retain fixed_decoded_temperature scope and explicitly do not certify full-inverse direction or propagate liquid property/saturation uncertainty.

Each internal face contains one shared liquid molar rate and donor enthalpy rate. The total energy decomposition includes liquid enthalpy explicitly, with its numerical projection recorded separately rather than treating the physical liquid energy as rounding error. The exact update combines both adjacent liquid fluxes and phase transfer before binary projection. No separate latent heat or pQ source is added. Closed liquid boundaries remain zero. No blocking discrepancy found in the reviewed closed assembly.

## Independent reference

Three nonuniform-width cells use source dry Cp and an explicit artificial liquid u=75T-300000 J/mol, v=1.8e-5 m3/mol. Manufactured liquid tables use permeability1e-15 m2, viscosity .001 Pa s and nonconstant relative permeability kr=.25+.5*S. Both internal liquid connections are active. The test duration is .25 s.

The oracle independently computes source sensible U from the printed polynomial, solves its aggregate U for T via brentq, computes pressure from the artificial-liquid volume closure, then manually forms liquid mobility, series Darcy resistance, donor molar flow and donor enthalpy h=u+pv. It never calls liquid_face_exchange or decoded_liquid_state as reference; it also does not use production column/storage aggregate evaluators or inverse routines as reference. It reuses gas caloric, water chemical equilibrium and gas transport primitives, so it is an independent assembly/inverse/integration comparison rather than an independent validation of all constitutive primitives.

DOP853 used 38 RHS evaluations. An initial independent RHS probe cost .001038 s. Production midpoint results:

| Steps | Maximum energy difference (J) | Maximum inventory difference (mol) |
|---|---:|---:|
| 2 | 9.181440400425345e-4 | 1.7567095872417227e-7 |
| 4 | 2.2608844301430508e-4 | 4.3256684290060576e-8 |
| 8 | 5.60976259293966e-5 | 1.07328015364061e-8 |

Energy refinement ratios are 4.060995/4.030268, inventory ratios 4.061129/4.030326. Both satisfy the predeclared 3..5 gate and support second-order convergence for this smooth manufactured test. Finite-step error is not zero and this is not an a priori time-error certificate.

For each accepted step the independent Fraction audit checks every cell's liquid, total water and U updates against both shared faces plus phase and signed projection corrections. It also checks global liquid change=-total phase+liquid projection correction, global total water/U internal cancellation, and O2/N2 balances. Both internal liquid integrals and their enthalpy integrals are nonzero; every physical energy term is present in the exact face decomposition. All assertions pass. Predictor corrections remain outside accepted-state conservation equations.

## Limits

No EOS/native-water trajectory was run. Actual source-material connectivity, mobility, capillarity, available volume and experimental matching remain unsupported. Nominal saturation-table interpolation is not propagation of physical or inverse uncertainty. This report does not independently test open-liquid boundary behavior or old-host regression; those require their separate test evidence. Material qualification remains false and the full model Goal is not completed by this result.
