# Reduced compatible free-slab mechanics and local energy allocation

Status: design derived from the actual repository definitions; no EOS execution, no production changes, no new material admission. References below are the primary implementation of this manufactured model, not external evidence that it represents sludge. Reviewed 2026-09-08.

## Definitions and scope

Cells i stack along x, reference volumes V0_i, diagonal deformation F_i=diag(n_i,t,t), common positive t and independent positive n_i. Current volumes V_i=V0_i*n_i*t². The reference slab, cell ordering and solid identities must agree. Inertia, shear and bending are absent. Fix an arbitrary rigid translation of the normal displacement; do not accidentally fix total thickness. Uniform external pressure pe>=0 acts on the whole outer boundary. Per-cell pore pressure p_i comes from the SAME stage's inventory, total energy and geometry storage inversion. Fixed incompressible solid inventory implies pore-volume rate equals bulk-volume rate. Temperature-independent skeleton energy is required for the subtraction-based thermal inverse used here.

Write S_ni and S_ti for elastic+interface Piola stress, one tangential principal component (yy equals zz). With theta_i=ln(n_i)+2ln(t), d_ni=ln(n_i)-theta_i/3 and d_ti=ln(t)-theta_i/3, the actual model gives:

    Urec_i = V0_i [K_i theta_i²/2 + G_i(d_ni²+2d_ti²)] + gamma_i A0_i t²
    S_ni = (K_i theta_i+2G_i d_ni)/n_i
    S_ti = (K_i theta_i+2G_i d_ti)/t + gamma_i A0_i t/V0_i
    Pvis_n = eta_i ndot_i/n_i²
    Pvis_t = eta_i tdot/t²
    D_i = eta_i V0_i [(ndot_i/n_i)²+2(tdot/t)²] >= 0

Require strictly positive eta_i. Existing energy provider admits zero viscosity, but this rate solver must reject it unless a separately designed algebraic/DAE model handles the singular case. Retain all original stretch/rate domain checks, fixed inventory checks and source identities. A0_i is explicitly per-cell internal-interface area, not automatically the slab face area; a mesh refinement must partition it consistently instead of duplicating a full specimen's surface energy into every new cell.

## Compatible quasistatic solve

Use tension-positive stress, pressure positive in compression. Define total mixture Piola stress T_ai = S_ai + Pvis_ai - p_i J_i/lambda_ai, J_i=n_i*t².

Each normal internal interface has the same current area, so force continuity and uniform outer pressure imply T_ni=-pe*t² in EACH cell. Hence:

    ndot_i = n_i²/eta_i * [(p_i-pe)t² - S_ni].                 (1)

The allowed tangential virtual displacement has ONE amplitude, common t. Its generalized force balance, counting both tangent directions, is:

    sum_i 2 V0_i [S_ti + eta_i tdot/t² - (p_i-pe)n_i*t] = 0.

Therefore:

    tdot = t² * sum_i V0_i[(p_i-pe)n_i*t-S_ti]
                 / sum_i V0_i eta_i.                         (2)

This is a volume-weighted global solve, not the arithmetic mean of per-cell free rates. Equivalently it is the V0_i*eta_i weighted mean of each cell's unconstrained free tangential rate. Two symmetric tangent directions supply the same factor 2 to numerator and denominator; do not retain the factor on only one side. Use actual represented V0_i consistently throughout.

Define the tangential constraint reaction in Piola units:

    R_i = S_ti + eta_i tdot/t² - (p_i-pe)n_i*t.                 (3)
    Q_i = 2 V0_i R_i                                         (4)
    sum_i Q_i = 0.

The cell's total tangential stress is T_ti=-pe*n_i*t+R_i; generally R_i is NONZERO. Thus individual cells are not each in free tangential traction. Q_i is the force conjugate to the cell tangent stretch prior to imposing compatibility. Its sign is fixed by (3), not freely selected in the energy ledger.

Important boundary qualification: (2) enforces the free side boundary in a generalized/resultant sense under the restricted common-t kinematics. For heterogeneous cells, uniform common t with purely diagonal piecewise stresses cannot in general also satisfy pointwise free lateral traction. A full 3-D free body would develop shear/edge fields or nonuniform transverse deformation; the reduced ansatz omits those fields. Call this a constrained/reduced slab mechanics approximation, not an exact pointwise 3-D traction solution. Normal force continuity is imposed locally; tangent equilibrium is imposed globally.

## Per-cell first law: the essential coupling

Evaluate skeleton powers independently from the returned represented rates. Contracting the normal balance and the two tangent balances gives:

    Urec_dot_i + D_i - p_i Vdot_i = -pe Vdot_i + Q_i tdot,     (5)
    Vdot_i = V0_i (t² ndot_i + 2 n_i t tdot).

For total cell energy E_i=Uthermal_i+Urec_i, use:

    Edot_i = heat/mass energy flux_i + body_i
             - pe Vdot_i + Q_i tdot.                         (6)

The new component is constraint exchange power Wconstraint_i=Q_i*tdot. Summed over cells it vanishes, but it must be present in each cell's energy equation: ignoring it changes local temperature, hence pressure and subsequent mechanics, even if the GLOBAL energy check passes. It can be negative or positive. It is not locally dissipative heat. Actual nonnegative D_i already appears when (5) is subtracted from (6), giving Uthermal_dot_i=flux+body-p_i Vdot_i+D_i. Do not add D_i, stored-energy rate, or latent heat a second time to the total-energy RHS.

A cell has no separate conservation invariant E_i+pe*V_i. Instead, with no transport/body:

    E_i(t)-E_i(0)+pe[V_i(t)-V_i(0)] = integral Q_i*tdot dt.

At constant external pressure, the GLOBAL independent endpoint invariant is:

    sum_i [E_i(t)-E_i(0)] + pe sum_i [V_i(t)-V_i(0)] = 0,     (7)

up to the registered integration and arithmetic budgets. With transport only internal face fluxes cancel. External heat/mass/body contributions must be integrated into the right-hand side. At time-dependent pe, use integrated -pe(t)*Vdot, not -pe_final*DeltaV.

Implementation should expose an explicit constraint-exchange component with its conservative internal classification, not call all cell work external boundary input. Independently rounded cell powers may not sum to bitwise zero: preserve per-component representation/quadrature residuals and audit the exact Fraction sum against an explicit arithmetic budget. Never force the last cell's work to minus the others without recording the correction and its effect on local identity (5). Also retain rate-solution enclosure versus fixed represented-rate evaluation errors separately, as in the single-cell API.

## Stage/data path and numerical acceptance

At every RK and terminal/event stage: construct one CurrentSlab from all n_i and t; decode each cell's thermal state at its actual current volume after subtracting its zero-rate Urec_i; obtain ALL p_i; then solve (1)-(2) jointly; evaluate every skeleton at the returned rates; form total-energy RHS with (6). Do not invoke the single-cell free solve to supply the tangent rate or return that rate as if authoritative during the storage inversion. Split point storage decoding from the global mechanical closure.

Mechanical vector remains (n_0,...,n_m-1,t), length m+1, not two values per cell. Preserve same-stage state identity, explicit stretch tolerance/scale, error estimator, positivity/domain checks, rejection rollback, phase writeback and event/common-time comparison for the ENTIRE vector. Failure of any cell's inversion or rate domain rejects the whole stage; do not partially update cells. Inventory/energy transport uses current geometry and exactly paired face fluxes. Fixed solid inventory restriction remains in force.

The new component and global internal cancellation need schema, accepted StepLedger, cumulative original-prefix audit and checkpoint serialization/replay support. No silent dropping by legacy two-component host guards. Mechanical state is integrated, not reconstructed from a time program. Conservation audits must use exact represented inputs plus recorded quadrature corrections, and parameter/source/model identities must include cell ordering, compatibility assumption and work allocation rule.

## Required tests before wet multistep claims

1. One-cell limit reproduces the existing free solver: R and constraint power vanish within arithmetic bounds. Homogeneous split specimen reproduces identical rates and total powers with extensive Urec/A0/solid inventory partitioned consistently.
2. Heterogeneous two-cell pure-algebra oracle (different pressures, viscosities and stretches): independently derive (1)-(2), verify individual normal traction, weighted tangent resultant, and NONZERO equal-opposite Q. Choose a case where arithmetic mean of free rates is wrong. Permuting cells must only permute local outputs.
3. Independently calculate each Urec_dot, D and Vdot from explicit potential gradients, not from the balance residual rearranged as zero. Check (5), global power and D>=0, with registered arithmetic enclosure and separate rate roundoff accounting. Include tdot=0 with nonzero opposite R: reactions may exist while their power vanishes.
4. Heterogeneous local-energy negative control: omit Q_i*tdot and demonstrate that local thermal evolution/identity fails although global external-work conservation can still pass. Verify cellwise accumulated constraint work and global cancellation at EVERY accepted prefix, alongside mechanical and energy ledgers.
5. No-EOS dry trajectory versus independent explicit-gradient DOP853 or comparable independent reference, testing each cell's energy/T and all mechanical degrees of freedom, plus global endpoint invariant (7). Refinement gates and tolerances must be registered before execution. A single successful global balance is insufficient.
6. Out-of-domain cell, near-singular or zero viscosity, extreme finite values, mismatch of references/inventories, and unrepresentable arithmetic must fail explicitly and preserve the prior accepted prefix. Rejected stages cannot leak local energy or tangent changes. Audit whole-vector event and checkpoint paths with nontrivial m>1.
7. Only then add bounded wet point/short-trajectory tests with actual per-cell inversion and recorded uncertainty bounds. Same-EOS cross-check validates coupling, not the EOS or material law. Internal transport is a separate extension requiring face-by-face conservation and geometry tests.

## Primary definition links and limits

- Repository `src/sludge_sandbox/skeleton_energy.py`, DiagonalSkeletonEnergy.evaluate: exact manufactured elastic/interface potential, Piola stress, Rayleigh dissipation and arithmetic scopes used above.
- Repository `src/sludge_sandbox/free_skeleton_rates.py`, solve_free_rates: single-cell pressure signs and independent power/traction diagnostics; explicitly single-cell, not a multicell implementation.
- Repository `src/sludge_sandbox/dynamic_solid_storage.py` and `docs/sandbox/DYNAMIC_SOLID_STORAGE.md`: total-energy subtraction, current volume and thermal inversion, conditioning on represented decoded pressure.
- Repository `docs/sandbox/FREE_SKELETON_RATES.md`: directional interface energy and the prior explicit warning against applying independent cell free rates to a continuous slab.

Equations (1)-(7) are a new analytic reduction of those specified model definitions, not a claim attributed to literature. No new external scientific fact or parameter is admitted here. The fixed-solid, temperature-independent manufactured diagonal constitutive law, idealized compatibility and omitted 3-D edge/shear effects remain explicit. Pressure/storage uncertainty is not covered merely by interval-enclosing the rate solve conditional on represented p_i. This design does not establish sludge sintering calibration, fracture, evolving solid composition, realistic pore geometry, full-brick convergence or complete firing validation.
