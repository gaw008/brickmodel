# Prescribed deformation: minimum host implementation contract

Status: design only. No production source/tests were changed and no EOS experiment was run. The next implementable slice is an explicitly actuated ideal-gas chamber network with prescribed compatible geometry. It is not a constitutive prediction of sludge sintering, and it must not be enabled for the existing wet solid host by adding an unqualified `−pore_pressure * bulk_volume_rate` term.

## 1. Existing contracts and the first admissible mechanical model

`ReferenceSlab.deform` already maps one normal stretch per reference cell and a common tangential stretch into compatible widths, shared face areas, cell volumes and positions. It provides no time derivative, material identity or shrinkage law. `ConservedState` stores extensive mol and J, and `Rates`/`StepLedger` already apply the same quadrature weights to all face exchanges and `cell_power_w`/`cell_work_j`.

`SolidFluidStorage` currently computes `Vavailable=Vbulk−sum(Nsolid*vsolid)` using constant solid molar volumes, then performs the real liquid/ideal-gas pressure and thermal-U closure. Its energy scope explicitly excludes strain/interface energy. `SolidFluidHeat` requires its transport area×width to match that fixed bulk volume and binds each exact fluid template object. Replacing only a geometric field would violate those bindings or silently leave transport/storage at different volumes.

The first new production class must explicitly support only `mechanical_regime='prescribed_cellwise_quasistatic_gas_chambers'`: each cell is a spatially uniform gas chamber whose moving boundaries are pressure matched to its current EOS pressure by ideal external actuators. Adjacent cells may exchange gas/heat through declared moving permeable partitions. They need not have equal pressures; in that case the internal partitions' actuator forces and work are part of the external mechanical system. The model is not a freely moving continuous gas, a momentum solver or a brick skeleton. There is no physical skeleton/piston mass/elastic/interface state in this declared chamber model; their absence must not be reused as an estimate that such energies are negligible in real brick.

For this model, positive work *into* cell i is `Wdot_i=−p_i*Vdot_i` (Pa·m³/s=W). Compression heats; expansion cools. The pressure comes from the same decoded N/U/T/current gas volume used by the transport operator. An unrelated furnace reservoir pressure is not an admissible substitute for this pressure-matching relation. Independently prescribing both a volume history and an incompatible external pressure history would require force balance/inertia/dissipation and is rejected in this first class.

The closed reversible gas benchmark uses `dU=−p dV`, constant Cv, common EOS/caloric R and fixed N, giving `T/T0=(V0/V)^(R/Cv)` and `(P/P0)*(V/V0)^gamma=1`, `gamma=Cp/Cv`. Variable Cp curves do not have a constant-gamma invariant. NASA's primary explanations explicitly tie pressure-volume work to the process path and the isentropic formula to loss-free adiabatic compression/expansion; these support this restricted benchmark, not porous-solid mechanics. Sources checked: [NASA work by a gas](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/work-done-by-a-gas-2-2/) and [NASA isentropic compression](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/isentrophic-compression/). The distinction is also required by `docs/sandbox/WORLD_SPEC.md`, “能量与物质交换”.

## 2. Kinematic API and geometric conservation

Add `src/sludge_sandbox/deformation_program.py`, owning two immutable, identity-bearing objects:

- `PrescribedSlabMotion(reference: ReferenceSlab, knot_times_s, normal_stretches_at_knots, tangential_stretches_at_knots, motion_id, version, classification, source_ids, source_asset_sha256)`. Normal data shape is `(knots,cells)` and tangential data is `(knots,)`; all stretches are dimensionless and strictly positive. Time is s. No default isotropy or material shrinkage parameter.
- `MotionSnapshot(time_s, current: CurrentSlab, normal_rates_per_s, tangential_rate_per_s, width_rates_m_s, face_velocities_m_s, face_area_rate_m2_s, volume_rates_m3_s, motion_identity, method_id, numerical_qualification)` from `sample(time_s)`; `breakpoints_s(start,end)` returns the program's interior nodes.

Use one initially narrow interpolation method: per segment `lambda=lambda_a+(lambda_b−lambda_a)*(3q²−2q³)`, `q=(t−ta)/(tb−ta)`. Its analytic derivative is `(lambda_b−lambda_a)*6q*(1−q)/(tb−ta)`. It is a convex interpolation of positive endpoints over the full interval, with zero velocity at both endpoints; concatenated segments are C1. This prevents a discontinuity of mechanical power at a program node. Current `integrate` does not expose left/right stage evaluation at the same knot, so merely adding breakpoints is insufficient to make arbitrary discontinuous velocities safe. Nonzero-jump velocity schedules remain unsupported until a one-sided integration contract exists. This interpolation is a declared prescribed motion, not a fit to measured sintering rates.

For reference width dX and common tangential stretch lt:

```
dx_i = ln_i*dX                 A = A0*lt²
V_i = A*dx_i                  A_dot = 2*A0*lt*lt_dot
dx_dot_i = dX*ln_dot_i         V_dot_i = A*dx_dot_i + A_dot*dx_i
w_face[0] = 0                  w_face[j] = sum(dx_dot_i for i<j)
```

The tangential term is essential: `A*(w_right−w_left)` alone misses side-boundary work when area changes. Keep the alternative identity `V_dot_i/V_i=ln_dot_i/ln_i+2*lt_dot/lt` as a numerical cross-check, not a second physical law. All cells use the same actual interior-face area; do not set each face to a neighboring cell's `J^(2/3)`.

Validate finite representability, increasing times, shape/identity, positive geometry throughout each segment, and consistency with `ReferenceSlab.deform`. Reject underflowed widths/volumes and coalesced float face positions. Never clip a volume or derivative. Freeze snapshot arrays using the bytes-backed immutable pattern from `integration._array`; `CurrentSlab`'s present writable-flag-only arrays must not become mutable cached program state. Geometry numerical rounding bounds/qualification must be distinct from unknown experimental uncertainty. Every stage samples the original reference geometry at absolute time; do not compound updates from the previously accepted width.

## 3. Gas host, work, and face accounting

Add `src/sludge_sandbox/deforming_gas_heat.py`:

```
DeformingGasHeat(base_model: GasHeatModel, motion: PrescribedSlabMotion,
                mechanical_regime, work_model_id, work_model_version,
                work_source_ids, allow_manufactured=False)
evaluate(state: ConservedState, time_s) -> DeformingGasHeatEvaluation
__call__(state,time_s) -> evaluation.rates
breakpoints_s(start,end) -> motion/program union
```

The constructor requires complete gas caloric/EOS/source identity and the declared chamber regime. In this first class each current chamber volume is entirely gas: no liquid, solid or closed-pore volume is silently set to zero or subtracted from an unknown input. The constructor must bind the entire reference geometry, not only its volumes: the base cell count must equal `reference.cells`; `base.face_area_m2` must match `reference.reference_area_m2`; every `base.cell_widths_m[i]` must match `reference.half_thickness_m/reference.cells`; and every base gas volume must match the product of that reference area and width. Use an explicit numerical comparison policy: exact integer count and finite positive geometry, with zero relative tolerance and absolute tolerance at most twice the larger ULP of the compared finite area/width/volume values. This tolerance only accommodates binary64 construction arithmetic, not different physical shapes or measurement uncertainty. Preserve the policy and observed residuals in constructor diagnostics. `virtual_design_choice` can describe prescribed geometry; manufactured physical coefficients still require their explicit existing opt-in. Existing frozen transport coefficients are only admissible here under an explicit manufactured/idealized network classification; do not infer a material permeability-versus-strain law from them.

At every evaluation:

1. Check unchanged species/caloric identity and full N/U shape; sample one immutable geometry snapshot.
2. Create a coherent instantaneous geometry view with **all** current `face_area_m2`, `cell_widths_m` and `gas_volumes_m3`. Decode T from the same unchanged extensive N/U, then form each p/concentration from that current volume. Never divide/regrid the inventories by J or pre-update their energy from a temperature curve.
3. Assemble each gas/enthalpy/conduction face once using its current A and two current half-widths; kinetics, if admitted, use the current cell volume rather than initial volume. Fluxes must be defined relative to the moving chamber/partition. Mesh motion does not itself transfer mol between material/chamber indices. Reusing a lab-frame advective flux would require an ALE conversion and is outside this first contract.
4. Compute mechanical power from those same pressures and `Vdot`, then assemble `cell_power_w`. The first class reserves this entire field for mechanical power; `GasHeatModel` currently supplies zero body power, while boundary heat is already a face-energy term. Reject an unpartitioned additional volumetric power provider in this first slice.
5. Return `DeformingGasHeatEvaluation(rates, motion, gas_evaluation, mechanical_power_w, pressure_for_work_pa, work_model_identity, source_ids, qualification)` with frozen arrays and full original gas diagnostics. No fabricated `SolidFluidHeatEvaluation` or duck-typed wrapper.

For one small compatibility edit, expose `GasHeatModel.evaluate(state,time)->GasHeatEvaluation(rates, temperatures_k, gas_states, source_ids)` by returning the already computed temperatures/gas states from its existing body; retain `__call__` as `evaluate(...).rates`. This avoids solving temperatures a second time merely to obtain work pressures and preserves the old callable contract. Its zero-deformation equivalence tests precede this refactor. Do not rewrite the transport kernels or relax their source checks.

The current formation enthalpy/internal-energy anchors remain unchanged. Boundary work is added once through `cell_power_w`; flow work is already included in the transported species enthalpy. Do not add another `p*Q` for the same gas stream. `StepLedger.cell_work_j` is then exactly the accepted quadrature of mechanical input for this slice, with all faces and work using the existing RK weights; discarded stages have no accepted work entry. It must not be reconstructed from endpoint pressures alone. If later hosts mix body heat and mechanical work in this field, introduce explicit per-component accepted-stage work ledgers before claiming separate work/heat auditability.

All interior mass/heat/enthalpy face contributions cancel in the global sum because each face is stored once. Mechanical work is not such a transport face: with unequal chamber pressures, internal actuator work need not cancel. For equal common pressure it reduces to `−p*sum(Vdot_i)`; internal normal-face motion cancels in that special case. Do not force cancellation at unequal pressures or report the sum as only a single outer atmospheric load. The retained gas enthalpy flux and actuator work refer to different boundary-relative mechanisms.

No change to `integration.py` is needed for this C1 first slice. Callers still explicitly pass `breakpoints_s=host.breakpoints_s(start,end)`. State and face indices remain fixed; no remeshing is supported.

## 4. Why the current wet-solid host cannot inherit this work law

A future `DeformingSolidFluidHeat` can reuse the same motion snapshot only after adding an explicit mechanical storage/work provider. It must rebuild a mutually consistent `SolidFluidStorage` and transport view at each stage: current Vbulk, solid phase volumes/closed-pore variables, pore/gas volume, common face geometry and all source identities must agree. The current storage's immutable exact-template binding must be satisfied, not bypassed.

Required additions are specific:

- A declared relation for skeletal strain/porosity and current solid/closed-pore volumes. Constant intrinsic solid molar volume alone does not prescribe bulk sintering shrinkage, closed-pore conversion or pore accessibility.
- A traction/stress/kinematic mechanical contract and energy split. In a deformable solid, stress power depends on the stress tensor and strain rate, including deviatoric deformation even when `Vdot=0`. Elastic energy, viscous dissipation and interface/surface energy need defined inclusion or an independently justified scope. A scalar pore pressure is not the macroscopic solid stress.
- If U retains skeleton elastic/interface energy, its value must participate in the same U→T closure (or in explicitly separate conserved state variables). If U is thermal only, the admissible thermal mechanical source must subtract changes in separately tracked recoverable/interface/kinetic energy from total supplied mechanical power. Unknown terms cannot be silently replaced by zero.
- For real liquid in a compliant prescribed chamber, a pressure-matched fluid-only piston model could be defined separately using actual `Vliq(T,p)` and fluid thermal storage. It still needs pressure/volume derivative error envelopes covering the current deformation path and a valid gas/phase domain. Existing fixed-volume `Cclosed` is a derivative at a frozen instantaneous volume, not `dU/dT` along a changing V(t). Gas may compress while liquid expands; `dVgas/dt` is not generally the externally imposed boundary-volume rate. Do not use `−p*dVgas/dt` as the sole whole-fluid external work.
- In a real porous skeleton with liquid/gas, stress partition, capillary pressure/interfacial energy, skeleton deformation and phase exchange must be mutually compatible. The current flat-interface liquid pressure equality is insufficient to supply any of these missing relations. Pore collapse remains an explicit domain exit.

Areias Figure 4 supplies finite digitized **total one-direction dL/L0 versus temperature** under its particular experiment, with digitization rather than full experimental uncertainty. `AREIAS2025_DIGITIZATION.md` explicitly does not admit a shrinkage constitutive law. Such a record does not establish both `lambda_n` and `lambda_parallel`, nor justify `J=lambda³`. Direction, engineering versus logarithmic strain, reference length/state and the separation of thermal expansion from irreversible sintering must be established. A future prescribed path may use an explicitly identified direction and schedule; it cannot label assumed transverse strain or fitted kinetics as measured data.

## 5. Independent acceptance gates before implementation

Create `tests/sandbox/test_deformation_program.py` and `tests/sandbox/test_deforming_gas_heat.py`. Register these gates before running:

1. **Kinematic identities:** mixed per-cell normal and common tangential stretch, positivity over entire smoothstep segments, common face area and face velocities. Compare analytic Vdot with the product identity and independent central differences away from knots (relative 1e-7 with absolute 1e-12 m³/s for a specified laboratory-scale fixture). Test exact zero derivatives at nodes, invalid identity/time arrays, nonpositive stretches, overflow/underflow and unresolvable face spacing. This is numerical kinematics, not material uncertainty.
2. **Closed reversible adiabatic oracle:** explicit manufactured constant molar Cp=30 J/mol/K, common registered R, N=1 mol, T0=500 K, V0=.01 m³; normal stretch 1→.8→1 with tangential stretch1 and no heat/mass exchange. Reference formulas use the initial state and actual prescribed V(t), never the candidate's evolved T/P. Three maximum steps 1/128,1/256,1/512 s over the declared 2 s path; finest |ΔT|≤2e-4 K, pressure relative error≤2e-6, dimensionless `(P/P0)*(V/V0)^gamma−1`≤2e-6, and |ΔU−N*Cv*(Texact−T0)|≤5e-3 J. Record observed convergence; require at least a factor3 error reduction on adjacent halvings unless already at a separately documented representation floor. All N remain unchanged, compression work positive, expansion negative; same-volume return approaches initial U. No water EOS is needed.
3. **Two-cell shared-face test:** explicitly manufactured nonzero relative gas exchange and heat exchange, unequal normal stretches but common area. Independently reconstruct each cell's and total N/U prefix from raw StepLedger fields. Interior mass/energy cancel to the existing integration tolerances (1e-12 mol,1e-8 J for the fixture). Total ΔU equals external face energy plus summed actuator work, including internal actuator work when pressures differ. A separate equal-pressure kinematic sample verifies cancellation of internal normal-motion contributions without assuming it for every trajectory.
4. **Zero deformation:** lambda=1 and all rates0 returns identical gas Rates to the fixed geometry host at the same N/U/time, including any reaction/outer boundary face; mechanical cell power is exactly zero. Compare conserved trajectories under the same ordinary policy within its existing tolerance. This refactor must not change source identities or admit absent material providers. Before implementation, add a constructor-rejection regression with `base.face_area_m2=2*A0` and every base width `dX/2`, while retaining the correct reference gas volume `A0*dX`: equal volumes do not make this host equivalent, because its face area and half-cell conduction/diffusion distances differ. Also reject a mismatched count, an isolated width mismatch and an isolated volume mismatch; only the explicitly declared ULP arithmetic allowance may pass.
5. **Boundary/source/domain failures:** explicit volume history with incompatible supplied external pressure is rejected; unknown solid/liquid/closed-pore content is rejected by this first class; no velocity jump interpolation, no arbitrary isotropy, no double flow-work term. Cancellation, property-domain exits and finite resource limits retain the last accepted state and full ledger. Body heat plus mechanical work without component ledger support is rejected rather than mislabeled.

These thresholds are proposed pre-registration, not results. Keep any failed run artifacts; do not change a threshold to manufacture a pass. Use one ordinary gas-only bounded run per gate before any expensive multiphase connection.

## 6. Implementation order and completion boundary

First implement and independently review the identity-bearing C1 motion provider and kinematic tests. Second expose existing gas evaluation diagnostics without changing its callable behavior. Third add the actuated deforming gas host and the closed single-cell analytic work test; then the two-cell shared faces and zero-motion regression. Only after those pass should the new host be considered connected to the Goal's prescribed-geometry gas/heat/work slice.

This does not complete free sintering, material-specific densification, real wet-brick deformation, skeletal force balance or cracking. Those require the explicit mechanical/constitutive inputs above; neither existing water accuracy nor published total linear strain supplies them automatically.
