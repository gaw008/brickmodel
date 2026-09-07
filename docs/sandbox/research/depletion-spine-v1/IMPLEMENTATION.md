# Candidate: event-local nested ordinary approach spine

Candidate only: `candidate_depletion_integration.py`, copied from current production depletion module and modified in this temp directory. Production source, tests, installation and physics inputs were not changed by this worker. Only AST parsing was performed; no imports, EOS, probes or tests. Root must review and execute independent no-EOS tests before application.

## Public API

- New frozen `NestedApproachPolicy(maximum_step_s, reuse_ordinary_spine=False, strategy_id='nested_wet_ordinary_spine_v1')`.
- `DepletionPolicy.nested_approach: NestedApproachPolicy | None = None`; None retains the old algorithm and ordinary/terminal coupling, callback count and numerical gates. New metadata is additive.
- `ManufacturedDepletionAdapter.deterministic_contract: tuple[str,...] = ()`. Requesting spine reuse without a nonempty immutable contract raises `ordinary_reuse_requires_deterministic_adapter_contract` before integration. This is an explicit promise about a manufactured callback, not an automatic proof that arbitrary Python code is deterministic.
- `DepletionRefinement` appends deeply frozen `comparison_details`, `phase_costs`, `approach_role`, `approach_cap_s`, `approach_safe_inventory_fraction`.
- `DepletionResult` appends deeply frozen `phase_costs`, `reuse_counts`, `approach_strategy`.

## Implemented numerical behavior

With nested policy enabled, event-local ordinary maximum step is min(nested.maximum_step_s, integration.maximum_step_s). It remains fixed while the existing terminal threshold is halved. Ordinary desired durations are min(ordinary cap, safe fraction*tau, remaining common horizon), independent of terminal threshold. Existing `integrate` executes each ordinary segment; no RK or absolute-clock arithmetic was edited.

With reuse enabled, `_WetSpine` stores only successful ordinary integration results and already evaluated wet observations. Its root token binds actual operator object, initial state object and energy identity, root time, common horizon, actual approach cap, safe fraction, candidate cell, interface modes, inventory indices and explicit model/source descriptors. Each trial has fresh list containers and original immutable roundoff totals. The trial follows the identical cached ordinary prefix and adds independently calculated terminal/dry work. No terminal panel, event writeback, switched operator, dry continuation or common-time observation is cached. Failure/partial ordinary segments are not inserted. Horizon reduction creates a new empty spine; changed event/model bindings fail explicitly. A committed event ends the old spine lifetime.

Candidate source identity checks use existing descriptors (`source_ids`, water source-asset digests, water implementation SHA, host energy identity) and do not introduce a generic hash system or imitate native backend checks. Existing freshly executed water observations retain the exact native source/configuration guards. Every terminal and common-time validation is freshly executed and its failures abort before commit. **The reusable records additionally assume the explicitly fixed runtime remains unchanged between evaluations.** There is no new general public no-EOS source/config validation API and no claim to intercept arbitrary monkey-patching between cache hits. Deterministic adapter contract and immutable shipped provider/model bindings are the cache-admission scope. Root should independently review that boundary against source-mutation tests.

## Independent approach check

Two consecutive existing terminal comparisons must pass all five original gates. Then another entirely independent proposal starts from the same event-search root with BOTH actual ordinary maximum cap and safe inventory fraction halved. It shares no spine or observations. Its full accepted ordinary endpoint grid must differ from the candidate's; otherwise status is structured unsupported / `independent_approach_grid_uninformative`.

The independent branch is compared with the twice-terminal-verified candidate under the same event-time, event/common amount, energy, temperature and pressure gates, including provider error radii. Failure yields unsupported / `independent_approach_comparison_failed`; this bounded first implementation does not automatically inflate limits or run unbounded outer approach refinement. A later explicit policy can refine the approach further. On agreement, the original twice-terminal-verified candidate is committed, not the independent branch. Reported event metrics are componentwise maxima of the terminal and independent comparisons; both detailed comparisons are retained separately.

If the independent post-event path reveals a closer second event, common horizon replans with the existing bounded restart limit and invalidates the prior spine and terminal-pass history. Its earlier compute cost remains charged. Both original terminal passes must be obtained again in the new horizon.

This is event-local approach verification. It does not independently refine the already globally committed pre-localization history, and it does not replace the original external whole-trajectory step-cap comparison.

## Accounting and rollback

Fresh `observe` calls and ordinary integrator evaluations are charged once in existing totals. Cached-node and cached-panel reuse are counted separately in `reuse_counts`; no reused work is reported as a new evaluation or panel. Five phase cost buckets (`ordinary`, `approach`, `terminal`, `dry`, `comparison`) contain actual evaluations/panels/rejections. Existing monotonic wall deadline, accepted-panel limit and rejection limit remain unchanged. Cancellation and resource checks run at each cache traversal as well as fresh observations.

`commit` is unchanged: it audits the complete selected branch's inventory, total energy, components and correction contributions against original cumulative prefixes before mutating global state, mode or totals. Cached ordinary edge objects are immutable and included exactly once in the selected path. Independent/failed branch corrections never affect global totals.

Comparison decomposition uses observations already required by comparison: separate event/common per-species absolute differences and maximizing index, event/common energy differences, nominal temperature/pressure differences and each path's error radii, ordinary endpoint grids, and terminal start/end times. It adds no EOS calls. Metadata containers are recursively detached into immutable mappings/tuples.

## Required root review/tests

1. Compare nested cached/uncached identical policy: byte-equivalent trajectory, ledgers, corrections and event metrics; different cost/reuse metadata and wall durations are expected.
2. Independent constant/time-linear liquid sinks plus a nonzero reacting spectator and work; unchanged nearest-downward Euler clock/writeback.
3. Deliberately biased coarse approach must not pass through shared-prefix agreement; record independent rejection or sufficient agreement against an analytic oracle.
4. Horizon reductions, event identity changes, source/model mutation, stateful adapter rejection, cancellation and actual budget exhaustion must leave only previously globally committed states.
5. Sum phase evaluation/panel/rejection costs equals original actual totals; reuse counts are not added to fresh totals.
6. Full old regression with default nested_approach=None, then installed source/native experiments only after review and source freeze.

## Review fixes after independent initial checks

Root reported the first independent five checks passed and the legacy candidate check terminated with 35 passed; this worker did not execute those runs. Only after root confirmed terminal status was the initial candidate preserved byte-for-byte as `candidate-before-review.py`, SHA256 `298fe64e1cbdf3d0bf88d179d6c462a9f089df3573f9f9d8d27f618474929ad6`.

The reviewed candidate now detaches all five DepletionEvaluation observation sequences into immutable tuples at the observation boundary before validation/storage. This prevents an otherwise deterministic callback's reused list buffers from changing cached or event observations. Existing Rates array ownership remains unchanged. An independent-approach comparison failure is recorded once with its actual cost; raising its structured terminal status no longer appends a second duplicate-cost refinement. AST parsing only was performed by this worker after these edits; root owns further tests. No physics, gates, terminal clocks or installation changed.

## Final acceptance binding fix

Root's strengthened source-contract fault run terminated with four failing descriptor cases and two passing guard/simultaneous cases. The failing candidate could return completed when source IDs or deterministic contract changed at trial terminal switches 8 or 9, after the last cached-edge binding check. This is a real acceptance-boundary hole, not a weakened test. The exact prior candidate is retained as `candidate-before-final-binding.py`, SHA256 `88a9e4f613a0b7cc2fa6c5543b3a5c9ce02c6203a5fc5cba5c8205e00682c8d9`.

The new candidate stores the fixed root binding for nested mode even when reuse is disabled. It runs normal cancellation/resource guards and compares this binding immediately before the independent approach trial and immediately before committing the chosen twice-terminal-verified path. A violation raises the existing structured `ordinary_spine_binding_changed` failure before global state/mode/ledger mutation. Horizon replanning checks the old binding before constructing a new horizon-bound token, so replan cannot whitelist a changed model/source contract. None of these checks evaluates EOS or introduces a source hashing framework. Legacy `nested_approach=None` execution and all physical/numerical gates remain unchanged. Worker performed AST parsing only; root owns all reruns.
