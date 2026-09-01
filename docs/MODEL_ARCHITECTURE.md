# Model architecture

## Scope and fidelity

This package is a synthetic virtual-screening engine, not a calibrated digital twin.

1. `config.py`, `units.py`, `validation.py`: canonical dry basis, temperature conversion, simplex/PSD/morphology/source checks.
2. `chemistry/formula.py`, `stoichiometry.py`: atomic formula parsing, dry-feed element inventory, balanced gas potentials and external O2 ledger.
3. `thermo/equilibrium.py`, `minimal_backend.py`: protocol and constrained pure-phase Gibbs minimizer. It is independently tested but does not claim complete oxide-liquid coverage.
4. `physics/kinetics.py`, `transport.py`, `sintering.py`: Arrhenius, Kozeny–Carman/effective-medium and SOVS-inspired reduced closures.
5. `models/l0.py`: 0D enthalpy/reaction/gas/sintering screening.
6. `models/l1.py`, `fvm.py`: cell-centered 1D half-slab finite volumes with center symmetry and exposed-surface heat/mass transfer.
7. `uq/*`: power-of-two scrambled Sobol policy propagation and rank sensitivity.
8. `inverse/*`: realizability transform, hard constraints, multifidelity shortlist and nondominated filtering.
9. `io/*`, `cli.py`: content-addressed artifacts, verification, CSV/Markdown reporting and target benchmark.

## Canonical inventory basis

Feed composition is `kg dry solids`. Wet-basis moisture is converted by

`m_water / m_dry = w_wet / (1-w_wet)`.

L1 gas storage uses `kg species / m3 initial reference bulk`. It is an extensive deforming-cell inventory divided by initial volume. Current pore concentration for ideal-gas pressure is derived using `gas_mass / (MW * phi_open * Jdef)`. Condensed inventory remains on the same reference basis; current porosity is derived after dividing by current `Jdef=V/V0`.

## Reactions and exact elemental ledger

The enabled synthetic reactions are free-water removal, balanced organic pseudo-component oxidation, kaolinite dehydroxylation and calcite decomposition. `reaction_potentials()` computes gas moles per kg dry, feed atoms released, external O2 and non-zero reaction enthalpy. Its `element_balance_residual()` is checked independently.

For each element:

`initial feed + initial forming water + external O2 = final condensed + stored gas + escaped gas + residual`.

Mass uses the corresponding wet green-body plus O2 ledger. Energy uses cumulative boundary and reaction energy states:

`rho_eff cp (<T>-T0) = Q_boundary + Q_reaction + residual`.

## L0

State:

`[T, alpha_r, gas_k(ref), ln(V/V0), gas_out_k(ref), Q_boundary, Q_reaction]`.

Kiln position is not optimized independently:

`s(t)=v_ref*speed_ratio*t`, with every boundary value interpolated from the fixed spatial map. Heat input is convection plus gray radiation. Gas source is stoichiometric and outflow uses the supplied surface mass-transfer map. Reaction heat uses the declared non-zero enthalpy assumptions.

## L1 finite volume

Domain is half thickness `x in [0,L]`, cell-centered, with `dT/dx=dc/dx=0` at the center. The exposed face uses

`q_in=h(T_g-T_s)+epsilon*sigma(T_wall^4-T_s^4)`

and `J_out,k=km*c_surface,k`. Heat and each gas species use conservative face fluxes; reaction and enthalpy source terms are local. `solve_ivp(BDF)` is used with a sparse dependency pattern; Radau is only a structured fallback.

A strict forward run computes both 21 and 41 cells. Reported convergence metrics are final open porosity, final linear shrinkage and maximum center-surface temperature difference. A nonconverged candidate is not L1 hard-feasible.

## Phase, porosity, sintering and quality

`liquid_fraction(T)` is explicitly an `ideal_pseudo` sigmoid closure with coverage flag, not CALPHAD. Reduced SOVS-inspired shrinkage evolves `ln(V/V0)` using temperature, particle scale and liquid fraction. Final porosity obeys

`phi_total = 1 - (remaining dry solid mass / rho_true) / V_current`.

Open porosity is `phi_total * connectivity`, and no second independent pore-loss term is applied. Density is conservation-derived. Water absorption, strength, stress and defect risks are proxies and always carry `proxy=true`/unresolved-for-certification metadata.

## UQ and inverse

Only `2^m` Sobol sample counts are accepted. Bounds are called policy intervals/distributions, never empirical confidence distributions. Model-form discrepancy is reported separately.

The inverse transform enforces feed and internal simplexes, ordered PSD, morphology and fixed-map speed bounds. Each L0 point is evaluated under four policy samples. Only hard-feasible designs enter a gas-risk-aware diverse L1 shortlist; each shortlisted design receives a base 21/41 check and another uncertainty scenario. Final Pareto filtering receives only L1 hard-feasible points.

The returned set is intentionally many-solution: ranked candidates, Pareto points, feasible windows, active constraints, rank stability and L0/L1 disagreement. No unique optimum is claimed.
