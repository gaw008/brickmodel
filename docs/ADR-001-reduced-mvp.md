# ADR-001: Reduced local research MVP

Status: accepted for synthetic research MVP.

## Decisions

- L0 lumped screening plus L1 cell-centered half-thickness finite volume; no L2 in this repository.
- Fixed spatial kiln map; inverse changes `speed_ratio`, never zone temperatures.
- Reference-volume extensive gas/phase inventories; current pore concentration is derived after deformation.
- Pure-phase Gibbs protocol is implemented and tested, while forward liquid remains explicitly `ideal_pseudo` with coverage gap.
- Reaction enthalpies are non-zero source/interval assumptions; unknown zero is forbidden for active reactions.
- BDF with sparse dependency pattern, Radau only on structured BDF failure.
- Direct extent integration preserves coupled gas/element conservation. Tiny solver overshoot is explicitly projected for output, recorded as `extent_projection_max`, and fails above `1e-5`.
- Bloating risk scale `4.5e8 Pa` is an explicitly synthetic defect-proxy normalization inside a broad unknown interval, not a measured pressure limit. It is never presented as a product or safety threshold.
- Environmental limits absent means `not_evaluated`, never pass.
- Inverse returns a robust constrained set/Pareto window, never a unique guaranteed recipe.

## Consequences

The package can execute without plant trials and can eliminate inconsistent synthetic regions, but scientific credibility remains limited by oxide-liquid coverage, closures and synthetic boundaries. Any real use remains behind human approval and independent validation.
