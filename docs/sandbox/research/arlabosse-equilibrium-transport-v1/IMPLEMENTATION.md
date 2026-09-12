# Equilibrium transport handoff

2026-09-12. Scratch module `equilibrium_transport.py`; no production edits, installation, EOS, native run, or long trajectory. Original source modules and other workers' files were preserved.

## Public calls

```python
init = initialize_equilibrium(
    column, states, flash_policies, project=True,
    maximum_wall_seconds=40., energy_roundoff_budget_j=1e-8,
    inventory_roundoff_budget_mol=1e-12,
    prior_energy_roundoff_j=Fraction(0),
    prior_inventory_roundoff_mol=Fraction(0), cancel=None,
)
run = integrate_equilibrium_transport(
    column, init, duration_s=1., steps=1, maximum_wall_seconds=40.,
    energy_roundoff_budget_j=1e-8, inventory_roundoff_budget_mol=1e-12,
    cancel=None,
)
```

Initialization must have `status == 'completed'` before integration. `project=False` performs no flash or state projection; it validates caller-supplied equilibrated states through actual column decoding, source/state correspondence, original inverse criteria and actual-pv chemical checks. This route still requires explicit prior accumulated fees when applicable.

Only actual `ControlledVaporColumn` / `LowMoistureSorptionColumn` / `LowMoistureSorptionStorage` are admitted. All base phase coefficients must be exactly zero, reversible interfaces are required, internal gas diffusion/Darcy are disabled, and the original T325–338 K/P90–110 kPa/W0–.15 limits remain. Caller must explicitly construct each base `InversePolicy` with temperature tolerance <=1e-8 K and energy tolerance no looser than its flash policy. This tighter *fixed-composition* temperature target is a numerical choice, not proof that the original chemical gates will pass. Default policies are not modified.

## Shared update and certificates

Each step uses one set of accepted slow rates and `_integrals` shared faces. Before any new flash it computes exact `Nt* = Nc+Nv+Dleft-Dright+Gleft-Gright` and `U* = U+Hleft-Hright` for every cell; negative Nt fails before any new state/flash/advance. Thus an outlet can remove more than the old vapor pool without constructing a negative temporary Nv. Only Utarget is projected for the flash input. All cells flash before final column decoding and chemistry checks.

At the new fixed-composition inverse point, `EquilibriumCell.actual_vapor` retains the actual returned vapor chemical state at actual pv. The recorded full residual is `mu_liquid + mu_ex - mu_vapor`, not merely phase `RT log(peq/pv)` or the separate consistency residual at peq. Both original full-mu and peq−pv tolerances are enforced. Each cell stores `fixed_composition_inverse`, original phase, actual vapor and optional nominal flash. `certified_equilibrium_temperature_bound_k` and equilibrium composition energy error remain `None`.

For each cell, the same exact `J = oldNc+Dleft-Dright-flash.exact_liquid` then goes into **one final `_advance` on the original old states and same faces**. Every final state must exactly equal its flash state. Per-cell delta Nc/Nv must equal that flash's separately recorded projection errors; delta U must equal the already-recorded Utarget projection. No second physical update, latent heat, phase enthalpy term or rigid-boundary work is added.

`EquilibriumStepLedger` retains origin rates, shared faces, exact Nt/U targets, U projections, nominal flashes, actual fixed-composition rates/cell witnesses, J, `ColumnRoundoff`, step costs and exact global balance residuals. The energy identity is `delta sum U = -outer.energy_j + sum(deltaU)`. Its separate Q/H display is `Q-H-outer.energy_decomposition_roundoff_j+sum(deltaU)`. The external face's water/H/heat readout errors, face decomposition, and internal moisture readout errors are all charged once alongside the final state projection. Only adopted projections are charged; root trial projections, repeated fixed-composition decoding, source uncertainty and truncation do not become arithmetic fees or physical proofs.

## Returned state and failures

`EquilibriumInitialization` contains `raw_states`, accepted `states`, `rates`, `cells`, optional zero-time `ledger`, `roundoff` property, policies, model identity, explicit prior and used fees, counts and failure trial. Integration rederives initialization ledger costs and checks `used = prior + initialization costs`; it does not trust a cleared used-cost field. Integration retains the accepted state/time/observation/ledger history via `SourceColumnRun`, with initialization and pending `failed_trial` attached. New steps use actual accepted inventories, never subtract past corrections from Nt again.

Trials retain partial candidates, exact targets, returned rates/cells, proposed states, roundoff, pending costs and last completed object/context. Contexts record semantic flash/advance arguments and frozen identities, not live provider graphs. Completed objects are saved before post-call cancellation/time checks. Between-step cancellation preserves reused accepted rates and previous completed context. Terminal elapsed/status use one clock sample; late resource failure preserves already-accepted prefixes. Whole provider calls cannot be preempted internally; parent owns external native supervision. Counts are top-level flash/column/actual-vapor calls, not nested EOS iterations; `_advance` is not counted as an EOS evaluation.

## Actual validation

- `RED01.log`: genuine missing-module collection RED before implementation.
- `GREEN01.log`: first 9 manufactured host tests passed. They exercise actual `_integrals`/`_advance` with explicit manufactured flash/column/source API responses, not EOS or material physics.
- `CANCEL_RED01.log`: 1 failure / 2 passes showed `replace(None)` on cancellation between accepted steps; fixed by creating the next trial before its guard.
- Independent `review/code/INITIALIZATION_RED01.*`, `TERMINAL_RED01.*`, and `CONTEXT_RED01.*` preserve failures for erased prior fees, completed status beyond wall budget, and unsavable live-provider context. All were fixed without changing physical parameters or tolerances.
- `GREEN06.log`: **12 author + 3 independent tests passed**, including global conservation with nonzero boundary decomposition, final projection correspondence, each fee once, carrier preservation, outlet greater than old Nv, negative total rejection, phase disablement, certificate distinction/full-mu gate, initialization accounting, atomic failure/accepted prefix, post-return raw object preservation, terminal clock and passive native-driver encoding.
- No actual material/native acceptance is claimed. Parent owns source/native case assembly, independent final review, installation and the separately planned one-step experiment.
