# Two-cell audit: independent numerical contract

Read-only preparation from current gas_transport.face_exchange, RigidFluidHeat._face/_enthalpy, conduction_rate_w and ordinary integration error control. No EOS/tests/provider import or production edits. Worker scripts/PLAN were not yet present on first inspection; therefore this is an audit contract, not execution approval. All proposed transport coefficients remain manufactured.

## Independent callback reconstruction

Save original per-cell inventories, actual current gas volume, T and its inverse bound, P and bound, gas species masses/R, current face area and cell widths, coefficients and initial/midpoint identities. Reconstruct intensives from N/Vgas (not bulk volume): ctot=sum(c), x_i=c_i/ctot, M=sum(x_i*M_i), rho=ctot*M, P=ctot*R*T, Y_i=x_i*M_i/M. Compare reconstructed values with stored decoded gases. Do not call production gas_transport helpers to generate expected values.

For internal face 1 set dl=width_left/2, dr=width_right/2, d=dl+dr and w=dr/d. Series diffusivity is d/(dl/Dleft+dr/Dright), or zero if either side is zero. Interpolate face T, P and x with w; account explicitly for the source constructor's floating normalization of the interpolated mole fractions. Reconstruct Mface and rho_face=Pface*Mface/(R*Tface).

Independent diffusion formula:

j_star_i = -rho_face*(M_i/Mface)*Dface_i*(x_right_i-x_left_i)/d.
S = sum_i j_star_i.
Correction donor is left if S<0, right if S>0, absent if S==0.
j_i = j_star_i-S*Y_donor_i.
Jdiff_i = area*j_i/M_i.

For the fixed zero-permeability pilot, Darcy velocity and every Jadv must be exactly zero. For any later nonzero permeability variant, reconstruct serial K*kr/mu, u=-mobility*(Pright-Pleft)/d, choose donor by sign(u) and Jadv_i=area*rho_face*Y_donor_i*u/M_i. Do not silently add this branch to the current scope.

A zero species diffusivity does not make its net flux zero: mass-frame correction can transport the carrier. Require corrected diffusive MASS sum close to zero with a floating arithmetic bound; do not require molar sum zero. H2O mass differs from carrier mass, so equimolar diffusion is not the implemented model.

Fourier heat is Q=area*(Tleft-Tright)/(dl/kleft+dr/kright), zero if either conductivity is zero. It is positive left-to-right for a hotter left cell. Use the current deformed dimensions. Check Q separately rather than inferring conduction merely from a nonzero total energy face.

IMPORTANT actual enthalpy convention: _enthalpy evaluates DIFFUSION at the common face_temperature_k. Only ADVECTION uses advective_donor_temperature_k. Therefore Qspecies=sum_i[Jdiff_i*h_i(Tface)+Jadv_i*h_i(Tadv_donor)] and face_energy=Q+Qspecies when liquid_transport is absent. In the pilot Jadv=0. Record h_i(Tface) through the existing source-bound caloric objects if necessary; reconstruct the combination independently rather than calling transport._enthalpy. This tests assembly/temperature convention and does not independently validate the source caloric law. No extra liquid or latent enthalpy term belongs in this face ledger.

Check actual field shape (cells+1,species)=(3,5), energy shape (3,), external faces 0 and 2 exactly zero, internal H2O diffusion nonzero, immobile A/B/liquid face columns zero, and finite represented rates. For floating arithmetic comparisons a fixed preregistered combined tolerance such as 1e-12 relative plus an explicit scale-based ULP allowance is suitable; choose and store the exact formula before execution. It must be based on compared term magnitudes (including cancellation), not an arbitrary tolerance large enough to hide the expected flux. A deterministic implementation identity makes these algebraic checks distinct from physical property uncertainty.

## Per-cell and global ledger gates

Each accepted step stores one internal face value, used with opposite signs in neighboring cells. Audit independently using Fraction(float(x)) for every stored amount/energy and face/source/work value. For each cell/species, reconstruct Nnext-Nprev = face_left-face_right+reaction_source within the original stored-ledger roundoff budget. Likewise Enext-Eprev = energy_face_left-energy_face_right+cell_work. Check each named component plus its stored residual equals the represented total work exactly. Preserve the existing absolute local/prefix roundoff thresholds; do not infer them from integrator local truncation tolerances.

Global internal face cancellation is EXACT in rational sums. Only external faces enter the global source balance; here they vanish. Audit global carrier conservation, global H2O+liquid conservation and per-cell A+B conservation, using the existing declared state/ledger residual limits. A/B reaction and phase transfer both enter reaction_species; independently sum their expected channels. The carrier may redistribute, so a per-cell carrier-constant assertion is invalid. For each accepted prefix compare total energy to initial total plus accumulated mechanical/body work. No all-faces-zero assertion from v5 may survive into the coupled case.

Require every liquid inventory positive for this short-wet scope; retain unexpected depletion as failure/domain exit. Initial and final per-cell current storage must be the very same objects bound to reactions/inverses at that evaluation. Preserve reference/source hashes before/after and exact physical initial inventories/temperatures in coupled/control runs, while allowing transport-dependent implementation identities to differ legitimately.

## Coupling significance: what the stored errors can and cannot prove

Ordinary integration uses LOCAL scales nscale=amount_absolute_tolerance+relative_tolerance*amount_scale and uscale=energy_absolute_tolerance+relative_tolerance*energy_scale. Its step-doubling indicator is max(norm(dN)/nscale,norm(dE)/uscale)*q/(1-q), with actual substep q. These are local error-control scales, NOT proven global endpoint error bounds. Summing them or calling nscale an endpoint uncertainty does not create a rigorous guarantee. A stored thermal inverse error bounds decoding of the represented state, not trajectory truncation or model error.

For temperature at a fixed pair of represented final states, the inverse intervals [T-Binv,T+Binv] are real decoding bounds. If abs(Tcoupled-Tcontrol)>Binv_c+Binv_0, their decoded temperatures differ even allowing those inverse errors. This is a statement about the numerical endpoints only; it does not yet establish a resolved ODE effect.

The smallest credible trajectory-effect audit adds one preregistered cap-halved run for EACH mode, with the same physical inputs and original error tolerances. Record dN_mode=abs(Nfine-Ncoarse), dE_mode and dT_mode. For an operational, explicitly NON-CERTIFIED resolution threshold, require a coupled/control difference greater than the sum of both modes' cap differences plus their appropriate inverse bounds, with an additional fixed safety factor (e.g. 4) and local nscale/uscale floors to avoid declaring a sub-control-scale perturbation significant. For temperature, do not simply convert uscale into kelvin: composition changes alter energy inversion, and a valid sensitivity/heat-capacity bound would also be needed. Use the actual cap T differences and inverse bounds; label the result empirical numerical separation, not statistical significance or a proven continuum-error interval.

If only one run per mode is budgeted, the comparison should report nominal endpoint changes and inverse-interval separation, mark full trajectory numerical significance UNRESOLVED, and still accept the independent callback/ledger experiment if those gates pass. Do not invent a missing error bound to make a stronger pass claim. A real failure to exceed preregistered effect thresholds is a result, not grounds to raise conductivity or alter the interval after seeing it.

An even cheaper rigorous instantaneous check uses the same decoded initial state: expected coupled-minus-control energy derivatives are the signed internal face energy, and species derivatives are signed gas face rates. This shows the actual transport assembly influences local derivatives with exact global cancellation. The nonlinear feedback question (transport-induced T/composition changes alter phase rates) requires the endpoint comparison qualification above. Ea=0 A/B kinetics remain temperature-independent and cannot support a claim of thermal reaction-rate feedback.

## Pending final review

Await final worker PLAN/script bytes before approving execution. Root owns the audit implementation; no duplicate fixture/build work is performed here. Require fresh bounded callback before trajectories, sequential source-qualified runs, preserved failures and no concurrent EOS. Keep the known .005 ordinary-knot failure separate; no new transport experiment repairs it implicitly.

## Fixed four-run comparison indicator proposed to root

Root has selected four short runs: coupled coarse/fine and zero-transport control coarse/fine, with fixed cap halving and unchanged k=1/D_H2O=1e-8 initial coefficients. Before execution freeze the following indicators per cell/component; they are empirical numerical resolution screens, not rigorous global ODE error bounds.

Let c denote coupled, z control, f fine and o coarse. For amounts define D_N=abs(N_cf-N_zf), R_N=abs(N_cf-N_co)+abs(N_zf-N_zo), and local floor L_N=nscale_c+nscale_z from the actual policies. Report resolved_amount_indicator only if D_N>4*max(R_N,L_N). For total energy use the same expression with actual uscale values. Always retain the raw differences/scales as well as the boolean; these thresholds cannot replace ledger-conservation gates.

For temperatures define R_T_mode=abs(T_mode,f-T_mode,o)+B_mode,f+B_mode,o, using stored total inverse temperature bounds at every corresponding endpoint. Define D_T=abs(T_cf-T_zf) and S_T=B_cf+B_zf+R_T_c+R_T_z. Report resolved_temperature_indicator only if D_T>4*S_T. Also independently report decoded_interval_separation=D_T>B_cf+B_zf. The extra factor and coarse/fine discrepancies provide a deliberately conservative operational screen; they do not certify global trajectory error. Keep every cell's signed temperature change and whether the thermal gradient decreases relative to the control; do not collapse opposing local effects into a cancelling global average.

Water/vapor/phase effects may remain unresolved with these fixed coefficients and short duration. In particular an endpoint vapor redistribution below the local amount scale must not be promoted to resolved coupling because it is nonzero. No rigorous phase-rate interval follows automatically from temperature errors: saturation pressure, gas partial pressure and inverse-state sensitivities also matter. Unless such an interval is already available from the actual provider, retain phase-rate differences as observed/noncertified and allow their significance to remain unresolved. The experiment can still establish the two-cell field, nonzero internal transport, exact conservation and resolved temperature response; it cannot claim every feedback direction passed.

All four runs must share declared physical initial N/T and geometry/motion; the mode differs only in transport settings. The fine run changes only the registered step cap/initial step. Compare identities against each mode's registered identity, not by asserting all four full implementation identities are equal. Use the same source provider identities for every mode, and verify source-installed hashes throughout. A failed run blocks its trajectory comparison, but does not erase a passed independent callback algebra audit.

## Frozen script and ledger audit review — approval

FINAL DECISION: APPROVE the first fresh bounded callback, followed by the explicitly sequential experiment stages only after parent inspects each actual result and its independent audit. No EOS/test execution was performed in this review. No blocking defect found in these frozen scripts.

Independently verified:
- PLAN.json SHA256 62c6f72747182d7da123d5d8e2afa527e61a4ca15c0d9918dd6f915db4910885
- fixture.py 6d480756862da864b00451703f570434da59952b3ceeeae924fe175d596b6545
- callback.py 8ff679d0ababc669c87cc91280b7334cbd539bf3fdb9f5927712a9c5cd9b8275
- wet_run.py 3d3ecfb347114711d2ec42f1d692a9b030ebbb54d63475d0d07aa5a444246bec
- run.py 5dbd3958303f28ef7d0086429ccd395da76aab1e30b8265c88d5a7d5e93c2024
- root audit_ledgers.py c982e5b1f629df9e12adb9ff543d2bbcd27226aa5ec968c192e5b49ce90028d0

All four script hashes match PLAN and scripts/audit parse. All 43 source snapshot modules independently match installed bytes and their registered hashes; all 16 water asset hashes match. This is actual file inspection, not reliance only on worker-reported identity.

The fixture builds two distinct SolidFluidStorage templates, a two-entry reaction storage binding, per-cell point/skeleton indices 0/1 and common two-cell reference/motion. Every per-cell transport array and each required gas diffusivity tuple is length two. Species layout is unchanged and independent of transport gas ordering. Approved HEOS, vapor and chemical providers share the declared selection. Both phase coefficients remain active; interface modes derive from the new two-cell host. Initialization recomputes total energies under each mode's actual host identity.

The current parameter choices agree with PLAN: two .01 m cells in a .02 m half-slab, area .01 m2, 300/301 K, differing initial vapor amounts, manufactured k=1 and H2O D=1e-8 versus zero-transport control, carrier D=0 and permeability=0, closed external boundaries, same reacting skeleton and prescribed motion. The interval and the two caps are represented powers-of-two increments. This is a short ordinary wet experiment with no depletion locator/writeback. It does not expand the material/source domain.

snapshot() records original decoded gas states/current geometry, original total inverses and storage identity flags, actual rates and source identity. Its additional transport._face invocation is labelled a reconstructed production sampling step, NOT the independent oracle. The sampled species enthalpies are at face_temperature, matching the actual diffusion convention. No additional thermal inverse occurs. The independent algebra formulas earlier in this report must be applied to these records; the callback's nonzero/shape assertions alone do not certify the flux formula.

The callback writes evidence before success assertions, verifies both cells' current binding/inverse reuse, A/B and phase rates, sealed external faces and exact zero control faces. The wet script requires a fresh same-mode passed callback, exact encoded initial state and mode-specific energy identity, saves the complete integration result before requiring completion, requires all saved states wet, and labels success pending independent ledger audit. The extra final snapshot is correctly disclosed as outside the integrator's internal cost but within the supervisor. Before/after installed identity failures force failed status.

The supervisor uses bounded argument-vector execution, rejects existing result names and invalid attempt paths, snapshots code/tests/data/PLAN inputs and same-mode callback inputs, uses 30 s callback or 150 s wet caps, and requires both complete status and exit zero. Actual policy keeps 120 s internal budget and two preregistered caps. Stage ordering remains parent-controlled; the launcher does not itself enforce all cross-run preconditions.

## Root ledger audit cross-review

The audit imports no model code. It reconstructs per-cell cumulative amount balance using signed faces and reaction terms and per-cell cumulative energy using signed energy faces and work, all in Fraction arithmetic. Local/prefix species tolerance is 1e-12 mol; local/prefix energy tolerance 1e-7 J. Global water/carrier tolerances are each 1e-12 mol; per-cell A+B is 1e-10 mol and analytic A is 1e-9 mol. Global energy uses 2e-7 J, explicitly the two-cell sum of the 1e-7 J local allowances, not a hidden per-cell relaxation. Named component plus residual equals represented total work exactly; cumulative component residuals and available cumulative solver ledgers are independently compared. External faces are exactly zero and one internal face cancels exactly across the two cells. Liquid remains positive in every saved prefix. The audit correctly avoids asserting per-cell carrier invariance.

The audit reports all_saved_prefixes_pass and separately solver_status; it does not by itself require a completed horizon, nonempty steps or the expected mode-specific nonzero internal flux. This is useful for failure-prefix evidence, but parent must NOT treat its success alone as trajectory completion. The wet-script completed status/endtime and callback/mode gates are required alongside it. Similarly internal_water_flux_seen/internal_energy_flux_seen are reported flags, not asserted coupled-mode success. Preserve a failing audit's terminal traceback/log as evidence; this simple audit does not itself create a failure JSON. These are explicit audit scope limits, not permission to label incomplete or zero-effect results complete.

No numerical effect indicator is asserted by these scripts yet. The previously proposed four-run comparison screens remain separately preregistered parent-owned work. Nonzero internal transport, source-qualified callback and conserved two-cell prefixes can pass even if water or phase endpoint effects are unresolved; no coefficient retuning or full P01/P16 admission follows automatically.

## Actual independent callback algebra execution

Implemented audit_callback.py (SHA256 91018c52c72400f5a281a5bb595b8d257d76c9fedc38a8cfffe4dd1da81a4e95) using the standard library only. Independent tg reviewer approved the frozen script before execution. Then audited both saved callback JSON files; no model import or EOS call was made.

Both callback-coupled-audit.json and callback-control-audit.json passed 63 checks each. Coupled reconstruction gives H2O internal flux -2.0770265569473015e-12 mol/s and carrier +1.3363639309472463e-12 mol/s, with the expected nonzero mass-frame correction despite D_carrier=0. Fourier contribution is -0.950000000904899 W, species enthalpy contribution +5.141632099764316e-7 W, and total internal face energy -0.949999486741689 W. Control reconstructed species flux, conduction and enthalpy flow are exactly zero. External faces/immobile columns and assembled shapes pass.

The frozen tolerance policy is 1e-12 relative plus 64 times the sum of ULPs of contributing output terms; every comparison records actual/expected/error/bound. Largest coupled error/bound is approximately 0.0078125; control comparisons are exact. Policy timing is explicitly preserved in each output: it was fixed AFTER inspection of the first coupled callback pilot and BEFORE the control callback/all trajectories. This is not retrospectively claimed as preregistration for the first pilot. These checks establish independent arithmetic replay and source-bound enthalpy assembly, not independent caloric physics or resolved trajectory feedback.
