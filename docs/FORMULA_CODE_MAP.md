# Formula-to-code map

| Scientific relation | Implementation | Verification |
|---|---|---|
| `T_K=T_degC+273.15` | `units.degc_to_k` | `test_temperature_and_dry_basis_conversions` |
| `m_dry=m_wet(1-w)` and wet-feed + forming-water inventory | `units.dry_mass_from_wet`, `models.common.build_context` | conversion + feed-moisture metamorphic tests |
| dry feed/component/oxide simplexes | `validation.validate_case` | validation mutation tests |
| formula → molar mass/element vector | `chemistry.formula` | `test_formula_parser_and_molar_mass` |
| dry-feed atom inventory | `stoichiometry.initial_element_inventory` | mass closure test |
| CHONS + finite `O2_initial + integral(boundary flux)` cap | `ReactionPotential.element_balance_residual`, `models.common.oxygen_available` | zero/finite/rich-O2 manufactured test |
| `k=A exp(-E/RT)` and `alpha=1-exp(-kt)` | `physics.kinetics` | analytic first-order test |
| `K=d32^2 phi^3/[C(1-phi)^2]` | `physics.transport.kozeny_carman_permeability` | positive/bounded closure test |
| Maxwell–Eucken + morphology ensemble | `effective_conductivity_ensemble` | distinct positive closures test |
| `min G, A n=b, n>=0` plus traceable composition-domain coverage | `thermo.MinimalGibbsBackend`, `thermo.coverage.assess_thermo_coverage` | manufactured Gibbs + missing-phase/out-of-domain tests |
| `s=v_ref*speed_ratio*t` | `models.common.boundary` | speed metamorphic test |
| reduced effective enthalpy ODE identity (not full physical energy conservation) | `models.l0.rhs` + cumulative heat states | adiabatic reduced-residual/honesty test |
| center-symmetric cell FVM | `models.fvm.finite_volume_laplacian` | uniform-field manufactured test |
| L1 convection/radiation surface flux | `models.l1.rhs` | L1 run + 21/41 check |
| `n_ref=m_ref/M_k`, `c_k,current=n_k,ref/(phi_open J)` in `mol/m3_current_pore`; molar Fick/surface flux mapped back by `M_k` | `models.fvm.current_pore_molar_concentration`, `conservative_molar_fick_rate`, `models.l0/l1.rhs` | H2O/CO2 different-molar-mass manufactured flux, phi/J/deformation, global conservation and L0/L1 low-gradient tests |
| `P_partial(t,x)=RT(t,x) sum_k[n_k,ref(t,x)/(phi_open(t,x) J(t,x))]` | `models.common.finalize_result`, `io.artifacts._forward_independent_semantics`, `_forward_deterministic_replay` | pressure trajectory/extrema derived both algebraically and from independently replayed ODE primary states; rehashed interior/extrema attacks |
| reduced SOVS-inspired `dlnV/dt=-rate` | `physics.sintering`, L0/L1 volume state | temperature monotonicity + state bounds |
| `phi=1-Vsolid/Vcurrent` | `models.common.finalize_result` | forward porosity bounds |
| `WA=100 rho_w phi_open/rho_bulk` | same | proxy metadata/artifact tests |
| `strength=sigma_dense exp(-b phi_open)(1-D)` | same | proxy metadata/artifact tests |
| `inventory+out-initial` residual | same | L0/L1 mass/element tests |
| `Qreaction(t)=-rho_dry <sum_r DeltaH_r alpha_r(t)>`; `Qboundary(t)=rho_eff cp(<T(t)>-<T(0)>)-Qreaction(t)` | `models.l0/l1.rhs`, `io.artifacts._forward_independent_semantics`, `_forward_deterministic_replay` | independently rerun ODE cumulative heat states plus algebraic identity at every point; coherent temperature/heat mutation rejected; complete physical energy is `not_evaluated` |
| Sobol `2^m` policy samples | `uq.sampling.sample_parameters` | reproducibility/bounds test |
| quantile propagation | `uq.propagation.propagate` | quantile ordering test |
| 12-coordinate physically coupled design transform | `inverse.transforms.design_from_unit` | one-at-a-time metamorphic sensitivity test |
| fail-safe robust quality/risk constraints and slack | `inverse.constraints`, `inverse.search._record_from_results` | 1/4, 3/4, 4/4 policy-failure + active-slack tests |
| strict Pareto dominance | `inverse.pareto.nondominated_mask` | dominated/NaN/infeasible test |
| deterministic Sobol design/policy seed schedule + multifidelity shortlist/Pareto pipeline | `inverse.search.run_inverse`, `io.artifacts._deterministic_inverse_replay` | ordered ID/decision/policy provenance replay; add/delete/reorder/source/decision/constraint/nondominance attacks |
| artifact SHA-256/size inventory + forward full-ODE trajectory replay + replay-derived artifact comparison + inverse full-solver replay | `io.manifest`, `io.artifacts` | byte tamper; coherent rehashed temperature/molar primary-state attacks; schema/unit/summary/count/envelope/CSV/source/Pareto attacks; provenance/solver digest attacks; explicit `not_evaluated`/integrity-only fields |

The oxide-liquid output is an `unresolved_screening_proxy`, not a Gibbs/CALPHAD phase result. Connectivity, pressure normalization, SOVS reduction, stress, strength, absorption and defect metrics are also closure-dependent. Their appearance in this table maps formulas to code; it does not upgrade them to first-principles constants.
