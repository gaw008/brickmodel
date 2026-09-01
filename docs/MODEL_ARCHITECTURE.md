# Model architecture

## Scope and fidelity

This package is a synthetic virtual-screening engine, not a calibrated digital twin.

1. `config.py`, `units.py`, `validation.py`: canonical dry basis, temperature conversion, simplex/PSD/morphology/source checks.
2. `chemistry/formula.py`, `stoichiometry.py`: atomic formula parsing, dry-feed element inventory and balanced gas potentials; `models/common.py` imposes a finite initial-pore plus boundary-flux O2 cap.
3. `thermo/equilibrium.py`, `minimal_backend.py`, `coverage.py`: protocol, constrained pure-phase Gibbs minimizer and honest composition-domain assessment. Forward invokes the backend, records the failure/coverage state, and never claims oxide-liquid coverage.
4. `physics/kinetics.py`, `transport.py`, `sintering.py`: Arrhenius, Kozeny–Carman/effective-medium and SOVS-inspired reduced closures.
5. `models/l0.py`: 0D enthalpy/reaction/gas/sintering screening.
6. `models/l1.py`, `fvm.py`: cell-centered 1D half-slab finite volumes with center symmetry and exposed-surface heat/mass transfer.
7. `uq/*`: power-of-two scrambled Sobol policy propagation and rank sensitivity.
8. `inverse/*`: realizability transform, hard constraints, multifidelity shortlist and nondominated filtering.
9. `io/*`, `cli.py`: content-addressed artifacts, verification, CSV/Markdown reporting and target benchmark.

## Canonical inventory basis

Feed composition is `kg dry solids`. Wet-basis moisture is converted by

`m_water / m_dry = w_wet / (1-w_wet)`.

L0/L1 integrate each gas species as conservative molar inventory `n_k,ref` in `mol / m3 initial reference bulk`. Every species has an explicit molar mass `M_k`; sources map `kg→mol`, Fick/surface transport uses current pore molarity `c_k,current=n_k,ref/(phi_open Jdef)`, and artifact/conservation mass storage maps back exactly through `m_k,ref=M_k n_k,ref`. For isotropic deformation, internal reference-area molar mobility is `D Jdef^(1/3)` and surface area is scaled by `Jdef^(2/3)`. Condensed inventory remains on the reference basis.

## Reactions and exact elemental ledger

The enabled synthetic reactions are free-water removal, balanced organic pseudo-component oxidation, kaolinite dehydroxylation and calcite decomposition. Wet-feed moisture and forming-added water both enter free-water mass/latent-heat potential. Organic extent is capped by finite pore O2 inventory plus the time-integral of configured boundary transfer; zero O2 gives zero organic oxidation. `reaction_potentials()` computes gas moles per kg dry, feed atoms released, O2 demand and non-zero reaction enthalpy. Its `element_balance_residual()` is checked independently. CO/VOC/NOx remain explicit coverage gaps.

For each element:

`initial feed + initial forming water + external O2 = final condensed + stored gas + escaped gas + residual`.

Mass uses the corresponding wet green-body plus finite O2 ledger. The current temperature ODE uses cumulative boundary and reaction energy states:

`rho_eff cp (<T>-T0) = Q_boundary + Q_reaction + reduced_effective_enthalpy_ode_residual`.

This is deliberately not labeled full energy conservation: variable condensed/gas heat capacities, escaped-gas sensible enthalpy and diffusive sensible-enthalpy transport are absent. The reduced residual is a numerical ODE check, not a complete physical hard-pass.

## L0

State:

`[T, alpha_r, gas_moles_k(ref), ln(V/V0), gas_out_moles_k(ref), Q_boundary, Q_reaction]`.

Kiln position is not optimized independently:

`s(t)=v_ref*speed_ratio*t`, with every boundary value interpolated from the fixed spatial map. Heat input is convection plus gray radiation. Gas source is stoichiometric and outflow uses the supplied surface mass-transfer map. Reaction heat uses the declared non-zero enthalpy assumptions.

## L1 finite volume

Domain is half thickness `x in [0,L]`, cell-centered, with `dT/dx=dc/dx=0` at the center. The exposed face uses

`q_in=h(T_g-T_s)+epsilon*sigma(T_wall^4-T_s^4)`

and `J_out,k=km*c_k,current,surface` in molar units. Heat and each gas species use conservative face fluxes; reaction and enthalpy source terms are local. `solve_ivp(BDF)` is used with a sparse dependency pattern; Radau is only a structured fallback. Sparse finite-difference Jacobian warnings are filtered only for SciPy's private zero-column perturbation-factor overflow/invalid multiply; finite state, solver success, conservation and bounds remain mandatory.

A strict forward run computes both 21 and 41 cells. Reported convergence metrics are final open porosity, final linear shrinkage and maximum center-surface temperature difference. A nonconverged candidate is not L1 hard-feasible.

## Phase, porosity, sintering and quality

`liquid_fraction(T, oxide_flux_index)` is explicitly an unresolved screening sigmoid, not CALPHAD/Gibbs liquid. It changes with amorphous network-modifier chemistry so oxide decisions are not phantom, while thermo status remains `not_evaluated_missing_oxide_liquid_database` (or out-of-domain). Reduced SOVS-inspired shrinkage evolves `ln(V/V0)` using temperature, particle scale and this proxy. Final porosity obeys

`phi_total = 1 - (remaining dry solid mass / rho_true) / V_current`.

Open porosity is `phi_total * connectivity`, and no second independent pore-loss term is applied. Density is conservation-derived. Water absorption, strength, stress and defect risks are proxies and always carry `proxy=true`/unresolved-for-certification metadata.

## UQ and inverse

Only `2^m` Sobol sample counts are accepted. Bounds are called policy intervals/distributions, never empirical confidence distributions. Model-form discrepancy is reported separately.

The 12-coordinate inverse transform enforces feed/internal simplexes, ordered PSD, morphology, wet-feed moisture, fixed-map speed bounds and bounded sludge density/cp/k/effective diffusivity. Every coordinate has a one-at-a-time physical-sensitivity test. Each L0 point is evaluated under four required policy samples. The default/configured policy allows zero failures; any solver/conservation failure makes the record robust-infeasible and remains serialized. Only hard-feasible designs enter a gas-risk-aware diverse L1 shortlist; each shortlisted design receives a base 21/41 check and another uncertainty scenario. Final Pareto filtering receives only traceable L1 hard-feasible points.

The returned set is intentionally many-solution: ranked candidates, Pareto points, observed candidate envelopes, slack-defined active constraints, rank stability and L0/L1 disagreement. Fewer than three paired points gives `insufficient_points`; an observed envelope is not a continuously validated feasible window. No unique optimum is claimed.

## Failure and semantic-verification lanes

Config loading performs only type-safe unit normalization; malformed top-level/kiln/profile/inverse containers reach the validator and return CLI exit 2 without traceback. Runtime `Exception` from forward L0/L1, inverse or benchmark is caught at the solver boundary (never `KeyboardInterrupt`/`SystemExit`) and atomically serialized as a no-result artifact with stage, reason, safe exception class/summary, provenance and manifest. Occupied output is preserved unless overwrite was explicit.

Forward trajectory schema 2.0 retains the primary/extensive states needed to recompute derived claims: raw/projected extents, internal/released gas inventories, molar conversion, volume, porosity, temperature and cumulative heat. Strict verification independently rebuilds the model context from resolved case/provenance and cross-checks all summary values plus mass/bulk-volume/element/O2/reduced-enthalpy ledgers and trajectory extrema/counts. Inverse verification derives policy quantiles/constraints/objectives/counts from `all_evaluations`, computes nondominance against all hard-feasible L1 records, and cross-checks Pareto JSON/CSV and observed-envelope sources. SHA-256 remains a byte-integrity layer, not the source of semantic truth.
