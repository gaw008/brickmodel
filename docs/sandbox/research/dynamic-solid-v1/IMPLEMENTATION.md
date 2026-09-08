# Current-state dynamic point storage candidate

Owned candidate only: `dynamic_solid_storage.py`, proposed destination `src/sludge_sandbox/dynamic_solid_storage.py`. No repository changes, tests, installation or EOS execution were performed for this candidate. Apply only after parent review; it is a complete new module rather than a patch to the prescribed-motion implementation.

## Contract

`DynamicSolidStorage` requires the original `SolidFluidStorage` template, an exact `DiagonalSkeletonEnergy` (not the reacting wrapper), one reference cell, positive viscosity, explicit manufactured opt-in, matching actual solid provider identity and complete fixed Ns. Original reference bulk-volume agreement is retained. Identity hashes the original template and error declaration and contains the skeleton's full original reference/potential identity. Current stretches, decoded temperature/pressure, inventories and rates are not inserted into model identity.

`DynamicStorageErrorBounds` names normal and tangential stretch intervals, additional bulk-volume and mechanical-energy bounds, source IDs and qualification. These spatial state domains replace the old time-dependent motion-error domain; there is no synthetic clock or prescribed-motion object. The error intervals must lie inside the original skeleton stretch domain.

- `forward(T, *, normal_stretch, tangential_stretch, liquid_mol, gas_mol, solid_mol, external_pressure_pa)` returns `DynamicSolidState`.
- `target(value_j,error_bound_j)` returns the existing explicitly bound `TotalEnergyTarget`.
- `temperature_from_total_energy(target, *, normal_stretch, tangential_stretch, liquid_mol, gas_mol, solid_mol, external_pressure_pa, temperature_bracket_k, policy)` returns `DynamicSolidInverse`.

## Computation order

1. Validate original template identity and fixed Ns, then evaluate skeleton at zero rate. The recoverable potential is independent of unknown future rate and temperature.
2. Deform the actual original `ReferenceSlab` directly using current `(n,t)`. Snapshot arrays use immutable bytes-backed storage.
3. Propagate the same reference-volume, represented-geometry, additional-volume, elastic reference-volume, interface numerical and additional-mechanical-energy bounds as the existing prescribed point storage. Rebind the thermal storage's actual current bulk and available pore volume; the original storage retains the single bulk-minus-solid subtraction and all positivity/pressure/error guards.
4. Forward thermal evaluation or total-E subtraction plus original thermal inverse produces actual T/P. Total-E addition/subtraction rounding and target error propagation remain explicit.
5. Only now call `solve_free_rates` at the represented decoded pressure. No assumed pressure/rate enters the thermal inverse. The returned free-rate record independently contains traction/power residual evidence.

`DynamicSolidState` exposes `thermal_state`, zero-rate `skeleton_state`, `deformation.current`, `free_rates`, `current_storage`, total energy/errors and immutable identity. `DynamicSolidInverse.thermal_inverse` can later be reused by a host's existing decoded-state validation; no second thermal inverse is required by this module.

## Deliberate limits

No host, RK callback, wet integration, transport assembly, reaction, depletion event, external pressure program or full firing-cycle claim is implemented. The module supplies no additional dissipative thermal source. A later host must use external traction/body power in the total-energy balance and retain recovery/D as diagnostics.

The free-rate solution is conditioned on represented decoded pressure. `thermal_state.pressure_error_bound_pa` and all geometry/energy bounds remain visible, but the algebraic free-rate numerical bound is not silently advertised as a combined thermal-pressure/constitutive uncertainty certificate. Additional energy uncertainty alone does not bound derivatives of the potential. Coupled rate-error propagation is a separate host/admission question.

Shared imports intentionally reuse existing `_digest`, `_num`, `_out`, `_upper`, `solid_provider_identity`, `TotalEnergyTarget` and energy scope. A later common-preparation refactor could remove repeated arithmetic, but this candidate does not change existing prescribed behavior to accomplish that.
