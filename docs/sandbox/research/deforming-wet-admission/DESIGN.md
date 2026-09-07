# Explicit wet admission of the prescribed deforming-solid host

2026-09-07. Read-only design against the actual installed/checkpoint modules. No repository edits, water EOS calls or wet trajectory runs. The existing dry host result does not certify this proposed wet composition.

## Observed blockers in the current call chain

`ProgrammedSolidFluidHeat.__post_init__` requires exact SolidFluidHeat. Its constructor and accessors read base.transport/storages/species properties. evaluate calls base.evaluate, then uses the reference `self.transport` for surface area, last half-cell thickness, gas face and donor enthalpy. Merely expanding its type whitelist would therefore use the wrong geometry for a deforming base. `_check_state` currently calls the old thermal check, which must continue rejecting tagged total energy on the old path.

`WaterPhaseTransfer.__post_init__` admits exact RigidFluidHeat, SolidFluidHeat and ProgrammedSolidFluidHeat. `_thermal_host` unwraps only one program layer; its field/type branches assume the result is rigid or fixed-solid. It uses that object for cell count, liquid index, manufacturing checks, water caloric/asset/reference matching and interface modes. evaluate invokes the real base exactly once and then reads base.storage_states. New DeformingSolidHeat has neither these convenience host properties nor the three evaluation projections expected downstream.

`depletion_integration.observe` already accepts WaterPhaseTransfer itself (and the explicit manufactured oracle). It reads raw.base_evaluation.storage_states and storage_inverses to construct T/P/error observations. The event and ordinary paths now preserve energy_model_identity and classified power components, with cross-segment schema/budget checks. No direct admission of a bare deforming host should be added: evaporation must still come through the actual water-transfer wrapper.

## Minimal concrete source scope

Four modules would change: deforming_solid_heat.py (small explicit projections/check adapter), programmed_solid_fluid_heat.py, water_phase_transfer.py, and only if an existing diagnostic contract cannot be satisfied, depletion_integration.py. No change is needed to the total point inverse, physical water chemistry, finite-rate law, ordinary integrator or liquid face algorithm. Do not introduce a generic protocol accepting arbitrary duck-typed hosts.

### 1. Preserve real inverse context; do not manufacture another thermal state

Add the following read-only properties to DeformingSolidHeatEvaluation:

- `storage_states -> thermal_evaluation.storage_states`.
- `storage_inverses -> thermal_evaluation.storage_inverses` (the ORIGINAL thermal inverse objects, not newly constructed objects).
- `gas_states -> thermal_evaluation.gas_states`.

Keep total_inverses, current_host, motion, original thermal_evaluation, energy_model_identity and full sources intact. Currently each total inverse's temperature_error_bound_k equals its original thermal inverse bound, which already includes the mechanical subtraction/target uncertainty supplied by point storage. Verify that equality in a regression. This projection preserves the old `inverse.state is storage_state` meaning; do not expose a total-point inverse as if its `.state` were an old thermal state. Future changes to the total error contract must update this projection explicitly rather than silently dropping a larger error.

Add only static inventory/configuration projections to the new host where existing consumers need them: species_order, gas_species_order, inventory_layout and coefficient_classification from its bound base_model. A `_check_state(state)` adapter may call its existing `_check(state)` and must enforce the new canonical total-energy tag and runtime binding. It must never call the old thermal host checker on total joules. These properties do not broaden any caller's explicit type whitelist.

### 2. Dynamic program admission and current geometry

Program constructor admits exactly `(SolidFluidHeat, DeformingSolidHeat)`. Explicitly resolve a reference configuration host: old base itself or new base.base_model. All original reference, species ordering, duplicate exterior boundary, coefficient identity and source/manufacturing gates remain. The new path additionally requires wrapper allow_manufactured for the admitted manufactured skeleton/relative-moving mechanics; a preapproved base permission is not sufficient to bypass wrapper permission.

At evaluate:

1. Query BoundaryProgram at the actual trial time, then call the admitted base.evaluate ONCE on the actual tagged state.
2. For a deforming evaluation, use its `current_host` and original thermal_evaluation as configuration/physical data. For the legacy path, use the existing base and evaluation. Do not reconstruct a new deforming base, invoke another inverse, subtract mechanical energy again or instantiate an untagged state containing total joules.
3. Factor the existing private surface helper to accept an explicit transport/configuration argument for the new path (or a dedicated explicit helper), while preserving the old two-argument path. Its area, outer half-cell width and conductivity come from current_host.transport. Surface temperature is still the nonlinear film/radiation-plus-half-cell solution; it is not gas/core temperature.
4. Current host transport also supplies `_face` and `_enthalpy`; use actual decoded gas T/pressure/composition and the complete dynamic reservoir. Do not accidentally use `self.transport` reference geometry in either heat or gas flux after selecting current context.
5. Modify only the existing outer face arrays; retain base reaction sources, cell power and the five-category component map exactly. Existing face enthalpy already contains stream flow work. Mechanical pore work remains solely in base cell power.

ProgrammedSolidFluidEvaluation.base_evaluation remains the actual DeformingSolidHeatEvaluation on that path. Its existing storage/gas projections can then delegate without hiding the total inverse. Add explicit qualification text identifying prescribed mechanics and conditional surface closure; do not relabel the result as the old fixed-solid evaluation.

`breakpoints_s(a,b)` returns sorted unique union of program.breakpoints_s and new base.motion breakpoints through the new base's existing method. Call BOTH methods so each independently validates the requested interval; do not accept an interval outside either program. Legacy fixed-solid branch retains its original program-only result. Endpoint knots stay excluded. This union does not authorize discontinuous forcing.

### 3. Water interface admission without chemistry expansion

Extend WaterPhaseTransfer's exact admitted base tuple by DeformingSolidHeat. The program wrapper remains its existing exact type. Split configuration lookup from execution:

- Resolve an optional program wrapper, then optional exact DeformingSolidHeat, then its exact SolidFluidHeat base ONLY for inventory indices, cell count, solid/fluid phase source identities, original liquid/caloric reference matching and static manufacturing gates.
- Keep a separate explicit reference to the actual execution base. evaluate calls it, preserving the real program/current mechanical evaluation and the tagged state. The current returned thermal storage states, not reference storage conditions, supply T, liquid pressure and gas pore volume.
- Include manufactured skeleton, motion/relative-moving mechanics and geometry in the wrapper's own gate, in addition to all current coefficient/solid/gas/liquid-transport gates. Include existing source chains and mechanics identity, without treating source labels as material qualification.
- Keep the original JoinedWaterVapor.low_model exact same-source matching to WaterChemicalPotential: method/reference/assets/R and actual water source. High joined-vapor bounds are NOT liquid chemical bounds.

The existing law remains `r=K*(peq(T,P_liquid)-p_H2O)` using the true current total-inverse temperature, liquid pressure and `p_H2O=N_H2O*R*T/Vgas`. Each active cell source is only liquid −r / H2O gas +r. Ns and all other columns are unchanged. Existing references already contain phase internal energy/latent energy; do not add phase heat to either total power or component powers.

Same-time event writeback holds total E, F and fixed Ns; therefore recoverable mechanical energy stays unchanged during that inventory-only correction. The next actual trial still closes liquid/gas volume and thermal energy at the current motion time. This does not authorize unlimited correction or relax the existing conservation/error budgets.

Preserve existing interface_modes None declaration semantics, exact-zero depleted admission, K identity, strict versus explicit metastable-no-nucleation policy, unsupported liquid reappearance and zero-vapor diagnostic behavior. For dry high-T continuation, strict unknown chemistry remains unsupported; metastable continuation must retain its explicit scientific qualification. Do not close the K module to manufacture a dry cycle.

Water breakpoints delegate to either a direct exact deforming base or its program wrapper; old rigid/fixed-solid paths stay unchanged. `_check_state` calls the true new checker on the new path. Static source lookup must never be reused as the tagged-state validator.

### 4. Depletion observations and error scope

With the evaluation projections above, current `observe` can consume WaterTransferEvaluation.base_evaluation without a new generic adapter or extra solve. Check by exact tests that:

- T and P are from the same current thermal state as phase/transport and work.
- Reported inverse temperature error is the original mechanical-target-aware thermal inverse error, equal to retained total inverse error under today's point contract.
- Pressure error remains conditional on fixed decoded T. Do not advertise it as a full pressure uncertainty including deltaT without a proved bound.
- Event comparison's energy array is tagged total energy on this branch. Its acceptance tests and component work are not converted to thermal-only units silently.
- Every retained state and terminal correction keeps the same canonical energy tag; every trial/mode keeps the five-category power schema, even if some components are zero.

Ordinary/terminal component ledgers and cross-path absolute residual budget have already been implemented; use them rather than a second bookkeeping mechanism. Event refinement currently compares N/Etotal/T/P, not each mechanical component's truncation error. The new admission alone cannot certify large cancelling component integrals. Actual mechanical/wet convergence validation must compare them separately.

## Tests-first sequence (cost gate required before any wet run)

1. No-EOS configuration tests: exact old/new type whitelist; wrong foreign host and wrong total tag reject; duplicate boundary and source/R/low-water-identity mismatches still reject; no manufactured gate bypass. Distinct motion/program interior knots union exactly; interval outside either fails. Verify old default None/index/replace behavior unchanged.
2. Dry actual current-host integration or single evaluations: instrument point total_inverse count, assert one per cell per trial and identity preservation of thermal inverse objects; reference and current A/d deliberately differ. Compare the surface flux against independent half-cell convection series resistance; use nonzero reservoir influx and donor enthalpy. Both direct and program-wrapped new host paths must preserve five components and total tag. Do not fake wet EOS during these wiring tests.
3. One actual wet state only after root's EOS cost probe: at a supported 293–500 K stable-liquid state with preexisting liquid, compare wrapper phase rate against an independent same-source peq call using the retained current T/P; exact column source signs, zero added heat, unchanged base mechanical components and correct error projections. This is physical callback admission, not a trajectory claim.
4. A short actual nonzero-motion wet trajectory after preregistering resource and numerical gates: closed system water inventory and fixed Ns; total energy ledger versus external work, evolving thermal energy and phase state; no second latent heat. A separate source-supported entropy diagnostic must use the actual state and common reference; do not invent carrier entropy or assert total entropy from local r*deltaMu alone.
5. Only after the short wet gate, the actual depletion→dry continuation experiment: keep original K, current geometry/program knot union, five components, state tag, fixed Ns and full corrected water/energy ledgers. Retain event time/common-time refinement, cost failures and any unresolved entropy qualifications. No long wet run is authorized by this design itself.

No quantitative wet trajectory threshold is invented here. Root's pending actual EOS cost probe and scientific fixture choice determine a bounded plan before implementation validation. This admission remains prescribed, manufactured skeletal mechanics with source-gated fluid calorics—not measured sludge behavior or free sintering.
