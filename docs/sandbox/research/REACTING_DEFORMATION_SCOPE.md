# Read-only audit: reacting solids under prescribed deformation

Inspected current repository source and tests only. No EOS, installation, tests or production edits. Mathematical expressions below are proposed balances under explicit existing manufactured assumptions, not material evidence or implemented behavior.

## Result

The rigid-bulk host already evolves solid inventories, solid occupied volume, pore volume, gas inventories and thermal temperature at conserved total thermal U. The prescribed-deformation host deliberately forbids reaction configurations and changing Ns. Joining these requires current-storage reaction rebinding and an explicit mechanical-energy composition contract, not simply removing a guard. Reaction-driven occupied-solid-volume change remains distinct from prediction of bulk shrinkage: prescribed motion still supplies Vbulk(t).

## Exact guards and dependencies

- `src/sludge_sandbox/deforming_solid_heat.py:66` rejects any non-None `base.solid_reactions` as `solid_reactions_not_admitted`. Lines 115–117 require exact current inventory equality with the skeleton fixed inventory (`fixed_solid_inventory_changed`), including initialization.
- `skeleton_energy.py:149–156` stores a nonempty complete fixed inventory; at least one amount must be positive. Lines 172–180 put its actual provider identity and fixed Ns in the model identity. Lines 183–187 reject any change in inventory keys or values.
- `deforming_solid_storage.py:144–151` requires exact concrete types, complete provider identity and skeleton inventory keys equal to all thermal solid phases. `_prepare`, lines 164–168, calls the fixed-Ns skeleton before calculating current geometry, so point storage independently rejects changing Ns.
- `_prepare`, lines 179–187, already recalculates pore space as current bulk minus sum(Ns*vs); thermal inversion and transport share this storage. `solid_fluid_storage.py:127–169` repeats closure at each trial T, includes molar-volume uncertainty, propagates pressure uncertainty, and sums Ufluid + sum(Ns*us). It supports varying Ns with constant molar volumes in T/P.
- `deforming_solid_heat.py:148` reconstructs current base with new storages and transport but retains its old reaction config. Removing the first guard would still fail `SolidFluidHeat.__post_init__`, lines 136–142: config storages must be the exact same objects as host storages. Bypassing that check would give incorrect kinetics: `SolidReactionConfig.evaluate_cell`, lines 147–150, uses its bound storage bulk volume for concentrations.
- `solid_reactions.py:92–125` binds phases, molar mass, common formation-energy/molar reference, actual provider identity and kinetic gas constant. Lines 139–145 verify decoded inventory against the row. Preserve all these checks during current-storage rebinding.
- `solid_fluid_heat.py:294–300` uses actual decoded T for stoichiometric sources and adds no extra reaction heat. `incompressible_solid.py:204–210` uses u=h_standard(T)-p_reference*v, h=u+p*v. Changed phase amounts therefore change U through their formation/caloric terms.
- Deforming host lines 141–149 makes one total-energy inverse per cell and shares each exact thermal inverse object with assembly. Preserve this and its energy binding.
- Deforming host lines 150–160 records elastic, interface, dissipation, pore and body power. The current `pore` entry is actually -p*dVbulk/dt, equal to -p*dVpore/dt only for fixed incompressible Ns.

## Balance to derive before implementation

For the existing single-pressure, constant-solid-molar-volume, quasistatic manufactured assumptions:

    Vs = sum(Ns_i * vs_i)
    Vp = Vbulk - Vs
    dVs/dt = sum(vs_i * reaction_source_i)
    dVp/dt = dVbulk/dt - dVs/dt
    E = Ufluid(T,Nfluid,Vp) + sum(Ns_i*us_i(T)) + Emech(F,Ns,...)

The Vs-rate expression assumes zero solid transport, as in this host; otherwise all solid inventory rates enter.

Do not replace aggregate -p*dVbulk by -p*dVp alone. Internal moving solid/pore surface pressure work cancels for the total solid+fluid cell: fluid-side -p*dVp and solid-side -p*dVs sum to -p*dVbulk. At fixed bulk with reaction-driven Vs changes and no external work, total U remains constant; adding +p*dVs as net heating creates energy. The two phase terms can be diagnostic-only with an exact summation residual; neither should be counted twice. Different phase pressures/capillary energy require additional derivation.

Do not add reaction enthalpy again: complete phase U already contains formation energy, and T is inverted at updated inventory/geometry/total E.

For a composition-dependent mechanical potential:

    dEmech/dt = (partial Emech/partial F):Fdot
              + sum((partial Emech/partial Ns_i)*Nsdot_i)
              + other internal-variable terms

External recoverable mechanical power is the first, fixed-composition deformation term, with the existing reference-volume convention. Composition terms belong to changing storage and exchange energy with thermal/chemical storage. Adding the full derivative as external power would cancel this exchange incorrectly. Existing `elastic_rate_w` and `interface_rate_w` are geometric derivatives, coinciding with full rates only at fixed Ns. Generalized names must distinguish them. Dissipation stays nonnegative and is counted once.

A temperature-dependent free energy additionally requires entropy/internal-energy conversion and changes to the total inverse. A minimum new fixture should explicitly restrict mechanical internal energy to T-independent behavior, rather than silently equating free energy and U.

## Smallest correct new interface

1. Preserve existing fixed-Ns types, identities and rejection tests. Add an explicitly manufactured reacting-skeleton contract/version. Immutable identity includes provider identities, reference state, complete formula and domain; current Ns becomes a state input, not a different model identity every RHS call. Reference inventory is distinct from a current-inventory constraint.
2. Provider accepts actual F, Fdot and complete Ns, returning mechanical internal energies, stress or fixed-Ns deformation power, dissipation, applicable Ns derivatives, numerical bounds and supported-domain classification. Explicitly declare any composition independence as a manufactured assumption only. Subsequently test a composition-dependent manufactured potential so Ns derivatives cannot be accidentally treated as external work.
3. Point storage rebuilds Vp from actual Ns/current bulk with existing error bounds and re-evaluates Emech each call. For a T-independent potential, subtracting current Emech and making one thermal inverse remains valid.
4. Rebind existing reaction config to precisely the new `current_storages` before constructing current SolidFluidHeat. Preserve network, binding providers, source identities and strict checks. Do not pass an unaudited volume float through a bypass.
5. Preserve complete inventory columns and zero solid-face transport; expose reaction diagnostics plus current bulk/solid/pore volumes and rates. Check dimensions/roundoff; no clamping negative inventory or exhausted pore volume.
6. Aggregate pressure work remains -p*dVbulk for this total-cell formulation. Document/rename the `pore` label in the new identity or add diagnostic phase-split fields without changing ledger sum semantics.

This joins reactions and prescribed deformation; it does not supply free-sintering motion, chemistry-dependent moduli/viscosity/interface area, closed-pore conversion or chemical reference strain. Those still require qualified constitutive sources and mechanical closure.

## Existing verification scope

- `test_reactive_solid_fluid_heat.py::test_finite_oxygen_closed_reaction_integrates_energy_elements_and_analytic_feed` integrates manufactured feed→char and char+O2→CO2 in fixed bulk: C/O/mass/U, oxygen limitation, analytic first-order feed, changing occupied-solid volume and rising T. `test_zero_oxygen_stops_only_oxidation_and_source_has_no_extra_heat` checks no additional reaction power. These are explicitly manufactured, not sludge chemistry.
- `test_deforming_solid_heat.py::test_dry_compression_analytic_and_actual_accepted_components` covers fixed-Ns compression and component work over three refinements. Its constant-composition T oracle is invalid for reacting heat capacities/formation offsets/occupied volume.
- `test_actual_two_cell_geometry_faces_and_no_second_inverse` covers current geometry, shared inverses and face conservation, without solid reactions.
- `test_missing_scope_inventory_and_identity_rejected`, point-storage tests and skeleton tests preserve Ns/provider/source identities; fixed-Ns behavior should remain guarded after introducing the new operator.

## Recommended next actual manufactured validation

Preregister and integrate a dry one-cell mass/element-balanced A(s)→B(s), unequal declared molar volumes and distinct formation energies, inert ideal gas, nonconstant prescribed bulk compression, and full thermal+mechanical U. Define exact fixture constants/error budgets transparently; do not name them sludge minerals. A T-independent coefficient permits analytic extent N_A=N_A0*exp(-kt), while retaining nonzero reaction energy and occupied-volume change. Derive an independent scalar thermal balance/oracle from total-cell first law with changing heat capacity/formation terms and -p*dVbulk. Do not use the production inverse itself as oracle.

Required limits: fixed-bulk reacting case conserves E despite changing pore volume; zero reaction recovers original compression; equal molar volumes remove reaction-induced pore-volume change; unequal volumes change current gas pressure; column permutation preserves results. First-order rates cancel bulk volume, so add a non-first-order current-volume callback/trajectory to detect stale config binding. Verify every accepted prefix for element/mass/E and component residuals, convergence at preregistered gates, exhausted-pore domain exit and immutable model/provider identity.

Next, a composition-dependent manufactured potential must have nonzero partial Emech/partial Ns and demonstrate thermal-U exchange at fixed total E without fictitious external power. Then combine established active water/depletion and moving two-cell transport without relaxing gates. These checks advance coupling; none qualifies real sludge or free-sintering constitutive laws.
