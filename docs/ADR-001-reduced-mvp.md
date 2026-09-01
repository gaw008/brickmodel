# ADR-001: Reduced local research MVP

Status: accepted for synthetic research MVP.

## Decisions

- L0 lumped screening plus L1 cell-centered half-thickness finite volume; no L2 in this repository.
- Fixed spatial kiln map; inverse changes `speed_ratio`, never zone temperatures.
- Reference-volume extensive gas/phase inventories; current pore concentration and deforming geometry drive Fick/surface flux as well as pressure.
- Organic oxidation is capped by finite initial-pore plus boundary-flux O2; CO/VOC/NOx remain explicit unresolved gaps.
- Pure-phase Gibbs protocol is implemented, tested and invoked by Forward. The bundled phase source cannot cover the oxide-liquid problem, so thermo cannot hard-pass and liquid remains an `unresolved_screening_proxy`.
- Reaction enthalpies are non-zero source/interval assumptions; unknown zero is forbidden for active reactions.
- BDF with sparse dependency pattern, Radau only on structured BDF failure.
- Direct extent integration preserves coupled gas/element conservation. Tiny solver overshoot is explicitly projected for output, recorded as `extent_projection_max`, and fails above `1e-5`.
- Bloating risk scale `4.5e8 Pa` is an explicitly synthetic defect-proxy normalization inside a broad unknown interval, not a measured pressure limit. It is never presented as a product or safety threshold.
- Environmental limits absent means `not_evaluated`, never pass.
- Complete physical energy conservation is `not_evaluated`; only the explicitly named reduced-effective-enthalpy ODE numerical residual is enforced.
- Every required UQ policy sample is fail-safe: any failure is robust-infeasible unless a prevalidated nonzero failure threshold carries a scientific basis.
- Inverse returns a robust constrained set, Pareto points and observed candidate envelopes, never a continuously proven window or unique guaranteed recipe.
- Nonempty outputs require explicit `--overwrite`; writes use a sibling temporary directory, atomic rename and retained rollback directory. Manifest hashes/sizes every non-manifest payload and strict verification also validates semantic state bounds/traceability.

## Consequences

The package can execute without plant trials and can eliminate inconsistent synthetic regions, but scientific credibility remains limited by oxide-liquid coverage, closures and synthetic boundaries. Any real use remains behind human approval and independent validation.
