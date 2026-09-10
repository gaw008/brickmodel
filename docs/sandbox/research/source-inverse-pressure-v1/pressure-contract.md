# Initial root existence and continuation: precise conditional contract

Read-only source review; no EOS execution. The initial pressure interval can imply root existence, not merely bound displacement of an already assumed root, provided the existing declared numerical/stable-branch assumptions apply throughout the pressure domain.

## Residual-to-root argument

At fixed reported T0 and fixed inventories, define the true-within-declaration closure

    G(P) = Nl*v(T0,P) + Ng*R*T0/P - V.

On the declared stable smooth liquid domain, vP<=0 and Ng>0 give -G'(P)>=bmin=Ng*R*T0/P_hi²>0. If a computed P0 has |G(P0)|<=epsilonF, then E=epsilonF/bmin produces G(P0-E)>=0 and G(P0+E)<=0 as long as that entire interval lies in the declared domain. Continuity plus strict monotonicity establishes a unique root there. This does not circularly require knowing the root first. At an equality boundary, a root may lie exactly on the domain edge; later temperature propagation needs an interior margin or a specific one-sided/domain extension proof.

RigidStorage.evaluate_at_temperature at rigid_storage.py:214–228 computes a downward-rounded gas slope lower bound and an upward residual error sum: |volume_residual|+volume_resolution+Nl*liquid_v_error. Its returned pressure_error_bound_pa is their upward quotient, and it checks P0±error inside the actual mechanical pressure bracket (which is contained in the envelope domain). The argument is conditional on the declared liquid volume error bounding the intended EOS at P0, correct representability/residual accounting, and the smooth stable true branch over the interval. Pointwise positive native compressibility checks alone do not prove that domain-wide assumption.

## Additional uncertain constant volume and local tightening

evaluate_wet_fluid at mass_wet_storage.py:44–92 first computes extra_global=available_error/bmin using the envelope P_hi, outward rounds and forms global_error>=fluid_error+extra_global. It requires the global interval inside the actual mechanical bracket. Combining the two residual budgets gives the same endpoint-sign argument for every fixed V in the declared volume interval. The initial nominal pressure need not exactly solve nominal closure.

Only after this global fence succeeds does it set certified_upper=min(envelope P_hi,P0+global_error) and replace the volume-only extra by available_error/(Ng*R*T0/certified_upper²), keeping the original fluid_error. This is justified: a nominal root is within fluid_error of P0, every volume-perturbed root is already within the global fence, and the entire segment between those roots lies below certified_upper. A smaller local derivative denominator is not justified before the global fence. All divisions/additions must remain outward rounded or exact Fraction. The final local interval is also checked against the mechanical bracket.

## Wiring checks required for the new source helper

- Actual typed SourceWetStorage, WetMixedState and SourceWetInverse; unchanged storage/source/backend/energy identities. Fixed dry mass equals the storage mass and all molar inventories match the inverse mechanical record; positive Ng and positive wet Nl under this API.
- Inverse target energy matches state totalU. Reported T/P must come from inverse.point.fluid.mechanical, with actual source temperature error and source total pressure error (not fluid-only). Error radii finite/nonnegative and consistent with the declared energy inverse record.
- Nominal available volume equals storage's constant test-volume value; available error equals its declared uncertainty and includes any representation contribution. Available-minus-error must be positive. No bulk/solid-volume substitution.
- Mechanical pressure bracket lies inside fluid envelope pressure domain; whole T0±eT lies in both source caloric and fluid temperature domains. Recompute source initial global/local pressure radii from the saved residual/volume-resolution/liquid-v-error, Ng/R/T and constant-volume error; retain the original full source error if it is more conservative. Reject an underreported saved radius rather than replacing it silently.
- Global initial fence must be checked before local tightening. A radius reconstructed from a single observed compressibility is not equivalent. Retain the nominal fluid-error fence and the volume-perturbed global fence as evidence.
- For temperature continuation use exact global L and require P0±(total_eP+L*eT) strictly inside the actual mechanical pressure bracket, not merely the larger envelope. This prevents exit while applying the implicit-function derivative bound. Whole-domain smooth/stable branch and whole-domain |uP|<=B are still explicit conditional assumptions. Bootstrap only after this fence.
- Do not infer smoothness from two pressure/T samples, infer branch existence beyond the original pressure bracket, ignore phase boundaries, or convert existing manufactured numerical envelope into independently verified EOS evidence. If any validity contract is missing, report unresolved/refused with its reason. No change to reported-P gates or event/material qualification follows.

No new backend call is needed to check the saved arithmetic contract. Independently certified whole-domain backend response/error control remains a distinct missing proof; this stage can honestly produce a fully specified conditional continuation enclosure.
