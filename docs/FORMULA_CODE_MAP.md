# Formula-to-code map

| Scientific relation | Implementation | Verification |
|---|---|---|
| `T_K=T_degC+273.15` | `units.degc_to_k` | `test_temperature_and_dry_basis_conversions` |
| `m_dry=m_wet(1-w)` | `units.dry_mass_from_wet` | same test |
| dry feed/component/oxide simplexes | `validation.validate_case` | validation mutation tests |
| formula → molar mass/element vector | `chemistry.formula` | `test_formula_parser_and_molar_mass` |
| dry-feed atom inventory | `stoichiometry.initial_element_inventory` | mass closure test |
| CHONS + external O2 reaction balance | `ReactionPotential.element_balance_residual` | reaction balance test |
| `k=A exp(-E/RT)` and `alpha=1-exp(-kt)` | `physics.kinetics` | analytic first-order test |
| `K=d32^2 phi^3/[C(1-phi)^2]` | `physics.transport.kozeny_carman_permeability` | positive/bounded closure test |
| Maxwell–Eucken + morphology ensemble | `effective_conductivity_ensemble` | distinct positive closures test |
| `min G, A n=b, n>=0` | `thermo.MinimalGibbsBackend` | manufactured Gibbs tests |
| `s=v_ref*speed_ratio*t` | `models.common.boundary` | speed metamorphic test |
| lumped enthalpy balance | `models.l0.rhs` + cumulative heat states | L0 energy residual test |
| center-symmetric cell FVM | `models.fvm.finite_volume_laplacian` | uniform-field manufactured test |
| L1 convection/radiation surface flux | `models.l1.rhs` | L1 run + 21/41 check |
| Fick diffusion + `km*c_surface` | `models.l1.rhs` gas blocks | species/mass conservation test |
| `P_partial=RT sum(c_k)` | `models.common.finalize_result` | pressure bounds in forward/inverse |
| reduced SOVS-inspired `dlnV/dt=-rate` | `physics.sintering`, L0/L1 volume state | temperature monotonicity + state bounds |
| `phi=1-Vsolid/Vcurrent` | `models.common.finalize_result` | forward porosity bounds |
| `WA=100 rho_w phi_open/rho_bulk` | same | proxy metadata/artifact tests |
| `strength=sigma_dense exp(-b phi_open)(1-D)` | same | proxy metadata/artifact tests |
| `inventory+out-initial` residual | same | L0/L1 mass/element tests |
| `stored-Qboundary-Qreaction` residual | same | L0/L1 energy tests |
| Sobol `2^m` policy samples | `uq.sampling.sample_parameters` | reproducibility/bounds test |
| quantile propagation | `uq.propagation.propagate` | quantile ordering test |
| physical design transform | `inverse.transforms.design_from_unit` | inverse constraints test |
| robust quality/risk constraints | `inverse.constraints` | inverse constraints test |
| strict Pareto dominance | `inverse.pareto.nondominated_mask` | dominated/NaN/infeasible test |
| multifidelity inverse pipeline | `inverse.search.run_inverse` | reproducibility + L1 candidates test |
| content-addressed artifacts | `io.manifest`, `io.artifacts` | CLI/artifact/strict verify tests |

`ideal_pseudo` liquid, connectivity, pressure normalization, SOVS reduction, stress, strength, absorption and defect metrics are closure-dependent. Their appearance in this table maps formulas to code; it does not upgrade them to first-principles constants.
