# Composition-dependent free slab closure: read-only next kernel design

No repository edits, installation, native EOS or fabricated material coefficients. This is the required next mechanism under the existing Goal. All proposed constitutive tests remain explicitly manufactured.

## Actual reusable pieces

ManufacturedReactingSkeletonEnergy is already a frozen exact-typed provider wrapping DiagonalSkeletonEnergy. It checks complete finite nonnegative current solid inventory with at least one positive component; reference Ns is identity/normalization only. q(N)=q0+sum(w_a*N_a)>0, temperature-independent; elastic/interface energy, Piola stresses, fixed-N deformation powers, viscosity/Rayleigh/dissipation are all q-scaled. Complete separately named elastic_composition_derivative_j_mol and interface_composition_derivative_j_mol dictionaries and outward Fraction numerical bounds are available. Identity binds actual reference model/formula/q0/weights and excludes current Ns. Existing source IDs inherit reference; weight choices are manufactured model metadata, not independently measured material evidence.

DeformingSolidStorage/DeformingSolidHeat already admit exact reacting wrapper under explicit reacting_manufactured regime, with matching original source/caloric identities, total-E subtraction and current storages. DeformingSolidHeat._check accepts current Ns only in that regime, rebuilds SolidReactionConfig storages to current geometry, and invokes original SolidFluidHeat._assemble_decoded. The assembler uses actual decoded T and actual current bulk V for ReactionNetwork.rates and returns complete species source arrays. No separately added reaction enthalpy is needed because phase reference energies are in storage.

CurrentSolidStorage and FreeSolidSlab instead require exact DiagonalSkeletonEnergy and exact fixed Ns and reject solid_reactions. free_slab_rates requires exact diagonal providers and directly reads viscosity_pa_s. These guards intentionally block composing current fixed code with changing Ns. Merely removing them would be incorrect.

## Equations and total-energy accounting

Per cell U_total=U_thermal(T,N,Vbulk)+q(N)*U_el_ref(n,t)+q(N)*U_interface_ref(n,t).
At fixed n,t the recoverable composition derivative mu_rec,a = w_a*(U_el_ref+U_interface_ref), in J/mol. Its actual rate is sum_a mu_rec,a*Ndot_a, not external power.

Full recoverable derivative:
    Urec_dot = Urec_dot_fixedN + sum_a mu_rec,a*Ndot_a.

Free closure at each stage uses current q and current pore pressure after total-E inverse. Reduced normal and tangent equations remain:
    ndot_i=n_i²/(q_i*eta_ref_i)*[(p_i-pe)*t²-S_ni(N_i)],
    tdot=t²*sum_i V0_i*((p_i-pe)*n_i*t-S_ti(N_i))/sum_i V0_i*q_i*eta_ref_i.

Tangential constraint reaction R_i=S_ti+q_i*eta_ref_i*tdot/t²-(p_i-pe)*n_i*t, constraint power C_i=2V0_i*R_i*tdot. As before its per-cell value need not vanish; only weighted aggregate is balanced. Final fixed-N power identity is:
    Urec_dot_fixedN + D - p_i*Vbulk_dot = -pe*Vbulk_dot + C_i.

Thus total-E RK RHS remains face enthalpy/conduction exchanges plus external_traction+mechanical_constraint+body, with true reaction sources in Ndot. Do NOT add sum(mu_rec*Ndot), a second reaction heat or D to cell_power. Composition energy changes alter T through solving U_total at every stage; subtraction inverse automatically retains that coupling. Diagnostics may report full Urec_dot, fixedN part and composition part separately, but the fixedN identity cannot be mislabeled a full derivative identity.

When solid molar volumes differ, Vsolid=sum(N_a*v_a) changes; Vpore_dot=Vbulk_dot-sum(v_a*Ndot_a). The prior fixedNs equality Vpore_dot=Vbulk_dot is invalid. Current storage must recompute actual available pore volume at every changed N. Using p*Vbulk_dot in the fixed-N virtual-work identity is still correct; converting it to pore work requires the explicit composition-volume term. Do not append ad hoc p*Vsolid_dot to total external RHS. A chemical affinity/second-law analysis must consistently include thermal/pressure and mechanical composition derivatives, not identify q's derivative alone as full chemical potential.

## Smallest coherent code extension

1. CurrentSolidStorage: explicit inventory_regime tail field ('fixed_solid' default, 'reacting_manufactured' opt-in) or a new exact typed reacting current point. Require exact provider type matches regime. Constructor uses reference_solid_inventory_mol only for complete keys, original real solid_provider_identity for binding; runtime reacting evaluate uses actual complete N and same q provider. Preserve zero-rate before inverse and all total-E target/geometry/error logic. Do not bypass allzero-solid rejection. DynamicSolidStorage existing singlecell defaults untouched.
2. Free rate provider seam: current effective viscosity MUST be q(N)*eta_ref, not reference eta. Provide an explicit source/identity-bearing fixed-composition response descriptor from provider (effective viscosity interval + state at actual N), or a small exact-typed dispatch helper using known wrapper's complete q formula. Do not estimate viscosity by off-domain unit-rate probes or finite differences, and do not pretend q is a constant property. Numerator stress bounds and denominator positive viscosity bounds need outward Fraction propagation. Re-evaluate actual final rates via same current wrapper; retain original log-rate/stretch checks, constraint work, all residual checks and source bindings. Rate identity binds law and regime, never current composition.
3. FreeSolidSlab: require allpoints agree explicit regime; fixed path still exact Ns and rejects reactions. Reacting path requires source-qualified SolidReactionConfig matching InventoryLayout/providers and explicit manufactured flag. Rebuild reaction config storages alongside currenthost storage/transport replacement exactly as existing DeformingSolidHeat does. Reject partial/mixed regimes until separately designed. Mechanical sources arise only through the real complete species array; no pseudo stretch species.
4. Evaluation diagnostics: include current q/effectiveeta, complete per-species mu_rec with existing numeric bounds and separately integrated instantaneous mu_rec*Ndot diagnostic at current complete source rates. Include actual solid-volume rate and scope labels to prevent interpreting bulk work as full pore work. This is diagnostic only; retain existing total power component schema. Work/error aggregation must not silently include diagnostic compositionpower as externalwork.
5. WaterPhaseTransfer admission can reuse exact FreeSolidSlab if its new explicit regime is inside that class; no bypass of caloric/chemical/provider checks. Generic mechanical depletion already preserves full N/E/n vectors, so no event rewrite should be necessary, but allzero solids/reaction-domain and competing liquid event guards must be retested. Chemical reaction changing liquid must satisfy existing net/gross evaporation event assumptions or fail explicitly; do not label reaction-driven disappearance as evaporation.

## Real blockers beyond software composability

- Existing ArrheniusMassAction is source-labeled kinetic law, not a full free-energy/affinity closure driven by q(N). It may be used as an explicitly manufactured verification source but cannot claim thermodynamic admissibility or real-sludge kinetics when mechanical free energy changes. Nonnegative entropy production under an actual material reaction law needs additional evidenced chemical potentials/activities and kinetic coupling; do not invent them.
- q0/weights/eta/surface area and reference solid caloric values remain manufactured unless separately admitted. Presence of source IDs or algebraic balance is not material validity.
- Current power/rate bounds condition on represented pressure/geometry/parameters; they are not full constitutive or coupled uncertainty envelopes. Preserve existing labels rather than converting comparison indicators into confidence intervals.
- Full 3D traction/shear, spatial convergence, real reaction network/high-T liquid phases and full firing/cooling remain unfinished Goal work; this bounded closure does not complete them.

## Preregistered verification order

No-EOS first: q=1 parity bitwise/combinedbounds; constant q!=1 checks viscosity AND stress scaling independently; unequal q/eta in2cells checks weighted tangent denominator (not arithmeticmean); current N changes identity-stable but rate/energy different. Zero externalpressure, closed dry reaction A→B with equal molar volumes isolates recoverable composition energy; exact or high-accuracy independent caloric+q inverse T verifies no addedchemical heat and real changingNs. Repeat unequal molar volumes to verify gaspressure/currentpore and full totalE, not fixed geometry shortcut. Analytic dE/dN finite-difference/Decimal plus actual metadata/source mutation/refusal/negative/allzero guards. Event/current source schema and whole mechanical ledger must remain intact. Separate benchmark transient coupled reaction/free mechanics under true totalE conservation and localconstraint work, then later preregister native wet run after sourcefreeze and resource estimate. Keep failed artifacts and original tolerance gates.
