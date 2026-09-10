# A concrete conditional pressure propagation path

Read-only derivation from current source/closure/response contracts. No EOS calls or new source facts are needed for the algebra below. It reduces the missing interface from an arbitrary new thermal-expansion envelope to an already declared caloric pressure-response bound, but does not convert that declaration into an independently certified EOS enclosure.

## Existing identities and missing certification

Fixed-state mechanical closure is

    G(T,P,V) = Nl*v(T,P) + Ng*R*T/P - V = 0.

Nl and each gas inventory are fixed during inversion; Ng is their positive total. V is the constant available-fluid volume (uncertain within its declared fixed interval), not a fabricated dry-solid volume. The no-capillary planar liquid pressure equals gas total pressure. The stable liquid branch has vP=-v*kappa<=0. The response identity is

    uP = -T*vT - P*vP.

Current source locations: rigid_water_gas.py:128–176 prescribed-T closure; water_properties.py:430–467 local Table3 response; _heos_kernel.py:170–186 native HEOS Table3 quantities D/B, positive stability D, dvdt/dvdp and dudp identity; water_heos.py:77–81 passes those local responses through. Pressure-independent energy reference offsets do not alter uP. SourceWetPoint T/P properties read fluid.mechanical; SourceWetInverse separately reports a T error. No existing interface proves the response inequalities over a whole T/P rectangle.

DeclaredNumericalEnvelope (rigid_storage.py:71–105) already contains B=liquid_abs_du_dp_bound_j_mol_pa. evaluate_at_temperature checks observed |uP|<=B at the evaluated point (lines178–181). That observed check is not a universal interval proof. The actual native constructor docs/sandbox/research/source-wet-storage-v1/run_native.py:35–39 explicitly labels B=1e-4 on310..350 K/1e5..1e7 Pa as explicit_conditional_numerical_test_envelope_not_independent_eos_certificate, source manufactured:source-wet-native-test-envelope-v1. This provenance must remain visible.

## Derivation requiring no separate expansion bound

Let Vg=Ng*R*T/P>0 and D=Vg-Nl*P*vP>=Vg. Implicit differentiation gives

    dP/dT = (Nl*P*vT + Ng*R)/D
           = (P/T)*(1 - Nl*uP/D).

For a smooth stable branch, fixed N/V, and a whole-box bound |uP|<=B,

    |dP/dT| <= (P/T)*(1+Nl*B/Vg)
              <= L = (Pmax/Tmin)*(1+Nl*B*Pmax/(Ng*R*Tmin)).

Units are Pa/K; Nl*B and Vg both have volume units. This works without assuming vT>=0 and without a separate upper bound on compressibility. It uses vP<=0, Ng>0, T>0 and an actual whole-domain uP contract. Nl=0 reduces to the exact ideal-gas slope boundPmax/Tmin; that is a future separate supported zero-liquid case, not permission to bypass current wet-trial positivity.

For decoded T0 with error eT and reported closure P0 with total error eP (including volume uncertainty), use exact rational interval arithmetic:

    Ttrue in [T0-eT,T0+eT]
    Ptrue in [P0-(eP+L*eT), P0+(eP+L*eT)].

The initial entire T interval must lie within both source caloric and fluid response domains. The resulting P enclosure must lie strictly within the stable pressure domain. A continuation argument is then available: G_P<0, a valid root at T0 for every allowed constant V, smooth EOS on the rectangle, and the derivative bound prevent exit through P limits before reaching the T interval ends. Phase/domain boundaries or a missing root for allowed V invalidate this argument. Do not obtain it merely by checking two endpoint flashes.

A safe tightening is possible without new EOS calls: first use the global declared rectangle to establish the enclosure; then use its P upper bound and T0-eT in the same formula for L2. The already proved enclosure ensures the path lies in that smaller box. A direct local slope substituted without this bootstrap would lack whole-interval justification.

For two fixed endpoint inventories (which may differ), derive each enclosure separately; then the pair upper bound is |Pa-Pb|+radius_a+radius_b. Reuse of the same volume uncertainty does not justify assuming cancellation unless a separately proved paired contract is supplied.

## Minimum implementable API and qualification

A pure helper could accept a typed bound record (T domain, P domain, B_uP, stability/branch semantics, exact liquid molar basis, water/backend/source hashes, qualification), endpoint bound record (T0,eT,P0,total_eP,Nl,Ng,R,constant-volume binding), and produce exact T/P intervals, L/global-and-bootstrap radii and domain checks. All scalar evidence must be exact Fractions derived from recorded binary64 or original Fraction inputs; outward binary outputs must be documented. Both source caloric and water domains, original source/energy identity, fixed inventories and constant-volume interval are mandatory. No generic type with an arbitrary 'certified' label should be admitted.

Separate statuses:

- conditional_declared_envelope_pressure_propagation: algebra/domain checks passed conditional on the existing numerical envelope and smooth stable branch; current native source belongs here.
- source_certified_full_inverse_pressure_enclosure: only after independent whole-box EOS/error/stability certification or a specifically validated interval backend is bound to this exact identity/domain.
- unresolved_domain_or_missing_envelope: inadequate branch, inventory, source, root existence or domain information; no gate pass.

Current pressure_comparison.py explicitly temperature_uncertainty_included=False and mechanically bound WaterPhaseTransfer/FreeSolidSlab semantics are not source coverage. Reuse its Fraction interval arithmetic patterns only; do not widen its type checks or borrow its certificate.

## What remains to prove, concretely

An implementation may now produce a nontrivial conditional full-inverse pressure enclosure using already saved data and B, without another EOS run. To upgrade to an independently justified source enclosure, prove on the selected liquid T/P box: smooth unique stable branch, vP<=0, |uP|<=B and numerical residual/model error covering the actual backend. The current Python/HEOS response methods certify only local positive D and small local identity residuals. Their advertised derivative_scope explicitly says not an interval bound. A grid of local responses cannot close the missing universal quantifier.

A future narrow certification should target the small actual T/P neighborhoods after a conservative conditional enclosure, using validated interval evaluation of the same IAPWS residual Helmholtz derivatives with density-root enclosure and coefficient/backend binding. That is a distinct source proof project, not an assumption that current callable double-precision HEOS provides directed intervals. No new hypothetical material constants, molecular weights or formation energies are needed.
