# Independent code review: manufactured reacting deformation

Reviewed the actual unstaged changes in `deforming_solid_storage.py`, `deforming_solid_heat.py`, `integration.py`, the new `reacting_skeleton_energy.py` and both new reacting test modules. Staged diff was empty. Read the full affected provider/storage/host files, `skeleton_energy.py`, reaction configuration/provider checks, decoded thermal assembly, integration component ledger call sites and relevant fixture definitions. Read `docs/sandbox/research/REACTING_DEFORMATION_SCOPE.md` and the temporary preregistered PLAN. Review-time file hashes and successful AST parsing are retained in `code-review-files.json`.

No reportable defect found in the reviewed implementation. Production and test files were read only. This reviewer ran no EOS, installation, trajectory or full suite, and did not duplicate the root's live test process. An AST parse is not a runtime result; actual test outcomes belong to the root's execution evidence.

## Mathematical and storage assessment

The new provider explicitly defines a manufactured, temperature-independent mechanical internal energy. It enforces q0 > 0, complete unique nonnegative weights, complete finite nonnegative current inventory and some positive solid inventory. q is computed as an exact Fraction of the normalized represented inputs. Each base output and its error bound are expanded to an exact interval, multiplied by positive q, and outward converted through the original `_output`. Scalar and Piola tuple bounds are preserved. Composition derivatives are w_i times the corresponding base energy interval; the immutable mappings retain a bound for each derivative. Overflow/underflow failures propagate rather than being clipped. The wrapped concrete fixed-N model is evaluated only at its immutable reference inventory, so its original current-inventory rejection is not weakened.

At each point call, the new provider receives current Ns; the existing thermal storage reconstructs occupied-solid and available-pore volumes from those same amounts and current prescribed bulk volume. Current mechanical energy is subtracted before the one existing thermal inversion and included again in the total result with propagated error and addition/subtraction roundoff. This is valid for the explicitly T-independent potential. A T-dependent free-energy law is not admitted by this class.

The host's external mechanical components use the fixed-composition deformation derivatives only. `elastic_composition_derivative_j_mol` and `interface_composition_derivative_j_mol` are not added to external power. Their energy exchange remains in changing storage as required by the chain rule. Aggregate pressure power remains -p times the bulk-volume rate. No reaction enthalpy or reaction-induced pore-volume heating is added to the total-cell energy. These choices match the declared common-pressure, prescribed, quasistatic manufactured balance; they do not establish a thermodynamically admissible reaction law or free-sintering model.

## Binding and regression assessment

The default regime remains fixed_solid. Concrete skeleton type and explicit regime must agree; fixed hosts still reject solid reaction configurations and changed inventory. New point and host identity tags distinguish reacting storage from fixed storage. The skeleton identity binds reference geometry/provider/model, q0, every weight, domain and arithmetic formula; current Ns does not change model identity. Adding exact Fraction serialization permits the existing reaction network to enter the full base-model digest without erasing numeric identity.

Reaction rebinding uses `replace(base.solid_reactions, storages=storages)`, preserving the network, aliases, actual phase providers, energy/molar references, constants and source identities while rerunning the original constructor checks against the exact new storages. The subsequent SolidFluidHeat constructor retains exact object binding to those storages and current transport templates. Decoded assembly receives the original thermal inverse objects, retaining inventory, volume, source and temperature checks and avoiding a second solve. In particular, nonlinear concentration kinetics read current bulk volume, not the old reference volume.

The integration schema admits a subset of one of the two complete allowed vocabularies. A mapping containing unique labels from both vocabularies is rejected. Existing per-call schema constancy and exact total/component summation residual checks remain unchanged. Shared `body`/`dissipation` labels remain semantically shared; the new host emits all five new labels.

The new tests target explicit analytic interface/derivative formulas, composition exchange at zero deformation power, preserved fixed model guards and immutable identity, numeric range failures, nonlinear current-volume kinetics, inverse object reuse, point pore-volume/temperature changes and actual dry constant/compressing trajectories with an independent scalar temperature RHS. Inspection confirms the scalar oracle uses declared fixture constants/analytic extent rather than calling the production inverse. Its displayed chemical energy difference includes the declared standard-pressure solid-volume correction, and the mechanical composition term includes both elastic and interface storage. No runtime pass is inferred solely from this source inspection.

## Remaining validation scope

This approval is for the reviewed implementation, not completion of the preregistered coupling program. The current two trajectory tests use a single step cap; they do not independently prove time refinement, spatial refinement, a nonlinear-kinetics trajectory, zero-reaction/equal-volume limits, inventory-column permutation, exhausted-pore exits, wet depletion or moving multicell reacting transport. Those are explicitly still required downstream checks, not fulfilled by this review. The existing fixed-host regression checks also require actual execution against the integrated tree. No real-sludge material, transport, reaction or free-sintering qualification follows from these manufactured fixtures.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE the reviewed manufactured reacting-storage and prescribed-motion implementation. Runtime and broader physical validation remain separate evidence requirements.
