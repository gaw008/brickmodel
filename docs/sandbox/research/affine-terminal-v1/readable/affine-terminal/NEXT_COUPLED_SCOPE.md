# Smallest next coupled spatial experiment

Read-only blueprint from current modules, ACCEPTANCE_MATRIX P01/P16 and the v5 fixture. No EOS, tests, source edits or installation. The live full suite is not touched. Root reports v5 both trajectories/comparison passed; this report does not independently re-audit those outputs.

## Recommended concrete deliverable

Build one **two-cell, externally sealed, temperature-gradient wet reacting slab** using the existing prescribed-deformation host. Require nonzero internal vapor flux and nonzero conductive heat exchange, active water phase transfer and A-to-B reaction in both cells, and current-volume/storage feedback. First complete a short entirely wet trajectory and a zero-transport control. This adds actual spatial coupling to v5 without simultaneously introducing another event algorithm, capillary constitutive model, furnace boundary or free-sintering law.

No new production physics module is required for this scope. The principal missing work is a provenance-labelled fixture, independent face/ledger assertions and bounded actual joined execution. Existing tests already show a two-cell prescribed host with nonzero gas/energy face flux in test_deforming_solid_heat.py::test_actual_two_cell_geometry_faces_and_no_second_inverse, but that fixture does not combine v5's active water, reacting skeleton and full wet trajectory.

## Exact existing API path

- rigid_fluid_heat.py::RigidFluidHeat contains per-cell storage, conductivity, species diffusivity, permeability, relative permeability, viscosity, temperature brackets and boundary fields. Its _face builds gas diffusion/advection with actual current distances and _enthalpy carries donor gas enthalpy.
- solid_fluid_heat.py::InventoryLayout and SolidFluidHeat accept complete per-cell solids/fluids and SolidReactionConfig. _assemble_decoded assembles each internal face once: gas exchange, Fourier conduction, and donor enthalpy into the shared face ledger. Optional liquid transport already exists, but leave liquid_transport=None for this smallest scope.
- solid_reactions.py::SolidReactionConfig(storages=..., inventory_layout=...) evaluates each cell. Bind both actual SolidFluidStorage objects, not a repeated one-cell config accidentally left length one.
- geometry.py::ReferenceSlab and deformation_program.py::PrescribedSlabMotion support multiple normal stretches per knot and a common tangential stretch.
- deforming_solid_storage.py::DeformingSolidStorage plus reacting_skeleton_energy.py::ManufacturedReactingSkeletonEnergy supply one point per cell. Each reference skeleton must have the correct cell_index, common reference geometry and the corresponding provider/inventory identity.
- deforming_solid_heat.py::DeformingSolidHeat.evaluate solves each cell total-energy inverse, reconstructs current storage, replaces transport face area/widths from current motion, and rebinds reaction storages. It calls _assemble_decoded with those original inverses; it does not perform a second thermal inversion.
- water_phase_transfer.py::WaterPhaseTransfer wraps that host with one coefficient and interface mode per cell. Its evaluate adds phase species transfer while preserving host energy/work; no extra latent heat is needed.
- integration.py::integrate handles the short all-wet trajectory. The existing integrate_depletion with affine_midpoint can be used later for separated two-cell events, but is unnecessary to prove the first spatially coupled wet interval.

## Minimal fixture construction

Start a new fixture from v5 ingredients, retaining the same approved installed HEOS, IdealWaterVapor, WaterChemicalPotential, A/B properties, source uncertainty, current energy model and 295..310 K inverse domain. Assign a new manufactured fixture identifier and explicitly list all transport coefficients as manufactured choices, not water-source facts or measured brick properties.

A simple first geometry is ReferenceSlab(half_thickness_m=.02, reference_area_m2=.01, cells=2), so each reference cell remains .01 m wide and 1e-4 m3, matching v5 per-cell inventory scales. This doubles the represented half-slab length relative to v5; it is a new two-cell example, NOT mesh refinement of the old one-cell domain.

Use normal_stretches_at_knots=((1.,1.),(.9,.9)) and tangential_stretches_at_knots=(1.,.9) at times (0.,1.). This retains the smoothstep motion and isolates spatial effects from heterogeneously prescribed strain. Build two storage templates and two skeleton/point objects with indices 0 and 1; matching template identity is checked by DeformingSolidHeat.__post_init__. Use the same manufactured q(N) coefficients and solid provider definitions in both cells.

Transport arrays must all have length two: storages, widths (.01,.01), conductivities, permeability, relative permeability, viscosity and temperature brackets ((295.,310.),(295.,310.)). effective_diffusivities_m2_s must contain both gas keys fixture and H2O with two values each. A conservative explicit pilot choice is k=(1.,1.) W/m/K, D_H2O=(1e-8,1e-8) m2/s, D_fixture=(0.,0.), permeability=(0.,0.), relative_permeability=(1.,1.), viscosity=(1e-5,1e-5). This gives diffusion plus heat conduction and disables Darcy flow; it does not claim P10's pressure-driven branch is validated. Keep outer_reservoir=None and outer_surface_temperature_k=None for closed external faces.

Use identical A/B rows but different wet temperatures/vapor inventories, for example amounts [[2.,0.,1e-8,1e-6,.001],[2.,0.,2e-8,1e-6,.001]] in the exact v5 species order and temperatures [300.,301.] K. Set both phase coefficients to 1e-6 mol/s/Pa and interfaces to existing_liquid. Initialize through host.state_from_temperatures(...,time_s=.5); never reuse/copy v5 total energy into a different geometry/composition identity.

Preregister a very short initial interval [.5,.5+1/65536], much smaller than v5's observed depletion time. The fresh callback must still check positive inventories/phase transfer and its own source-domain validity; the short time estimate is not proof that depletion cannot occur. If an interface vanishes unexpectedly, retain a domain/event failure rather than clamping inventory. Resource caps remain explicit and bounded; do not extrapolate single-cell runtime as a guarantee for two inversions per callback.

## Verification and changed ledger expectations

At a fresh two-cell callback require shape (3,5) for face species and (3,) for face energy, exactly zero EXTERNAL faces 0 and 2, nonzero H2O face 1, nonzero initial thermal gradient and independently computed conductive contribution. Compute Fourier heat from actual current area and two half-cell distances using k, and independently compute the actual mixture-averaged diffusion in gas_transport.py::face_exchange: interpolate face p/T/mole fractions, form j_star[k]=-rho_face*(M_k/M_mean)*D_k*(x_R[k]-x_L[k])/distance, add the shared upwind mass-frame correction -sum(j_star)*Y_donor[k], then multiply by area/M_k. This is not an independent concentration-gradient Fick law. Confirm assembled face energy equals conductive heat plus actual donor-species enthalpy transport. Do not count net face energy alone as proof of conduction; advective/diffusive enthalpy can also generate it.

For every cell require current_reaction_storage is current_storage, thermal inverse reuse, correct geometry/pore closure, local A loss/B gain, water phase source balance and no added phase power. Check total source species separately from transport. A/B are immobile, so their per-cell A+B remains fixed; total H2O+liquid is conserved globally. Gas carrier is globally conserved but need not be per-cell fixed even with zero carrier diffusivity: the shared mass-frame diffusion correction can transport carrier. Check that correction and its enthalpy contribution explicitly.

The v5 audit's assertion ALL face fluxes equal zero must be replaced. Sum the two cell balances using exact Fraction ledger sums: the SAME internal face value enters with opposite signs and cancels exactly. Global energy change equals total named mechanical/body work plus external face balance; here the latter is zero. Each local energy change must include its signed internal face energy. Preserve all existing tolerances, correction accounting and independent source identities. Do not accidentally compare a cell's energy change to work alone.

Run one matched zero-transport control (k=0, all D=0, same mechanical/reaction/phase settings), reconstructing initial energy under that control's actual identity. Compare temperatures, local vapor inventories and phase-transfer rates; require change exceeding the recorded numerical/inverse-error uncertainty, not merely !=. This shows transport -> T/composition -> phase-transfer feedback. Existing Ea=0 A-to-B kinetics are temperature-independent: do not claim T -> solid reaction-rate feedback from this fixture. A later separate manufactured Ea>0 case is needed for that direction, with its own explicit kinetics declaration and oracle.

## P01/P16 limits and next gate

P01 requires grid/boundary/scale justification and convergence. The proposed two-cell experiment supplies spatial assembly/ledger evidence only. After it passes, hold the .02 m half-thickness fixed and refine 2 -> 4 cells with inventories/solid volume/interface area scaled consistently, sampled temperature/composition profiles, and face conductances determined by geometry. Changing total length or copying 2 mol A unchanged into each refined cell is not a mesh-convergence experiment.

P16 remains pending for the full brick process. The coupled transport switch can add evidence for wet thermal/composition/geometry interaction, but prescribed motion does not respond to stress or temperature, Ea=0 reaction lacks thermal-rate feedback, and the A/B skeleton and transport coefficients remain manufactured. Free sintering, real-material rates, capillary water transport and the full firing/cooling trajectory are not provided by this extension.

## Suggested new files and order

Use a fresh temporary preregistered package with fixture.py, callback.py, wet_run.py, compare_transport.py, run.py and PLAN.json, modelled on v5's source/installed hash capture and supervisor. If repository tests are added after the freeze, a focused tests/sandbox/test_reacting_wet_two_cell.py should cover assembly dimensions, current binding, independent internal-face formulas, shared-face cancellation and zero-transport control with manufactured arithmetic; native tests must remain explicitly source-qualified. Existing production modules need no speculative refactor.

Execution order after the live suite terminates: review/freeze inputs; fresh callback; inspect; one short wet run; inspect full local/global ledgers; control run; inspect; compare. Only then choose either fixed-domain mesh refinement or a separately preregistered separated-depletion extension. Do not initiate native execution from this blueprint.

## Separate known bug

The historical ordinary integrator .005 program-knot sequence can report unresolvable_stage_time. Its retained second-integration-tests.xml and earlier fixtures in /private/tmp/brick-affine-terminal-v1 remain independent reproduction evidence. It has not been fixed by affine terminal work. Keep its diagnosis/fix in a separate bounded task; do not hide it by calling the next smooth .5-start trajectory a regression fix for knots. The new two-cell construction itself requires no modification to that ordinary-step code.
