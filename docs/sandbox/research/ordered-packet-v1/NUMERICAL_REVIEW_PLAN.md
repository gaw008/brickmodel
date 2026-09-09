# Ordered affine packets: bounded numerical review plan

Read-only current-core review; no native calls or source edits. Contract is the existing sampled-affine numerical localization plus two consecutive refinements and independent finer approach. Do not require a new validated true-ODE remainder, and do not claim one.

## Minimal interfaces

Use a frozen `PacketEventFrame(event, corrected_state, observation, pressure_snapshot, mode_before, mode_after)` and a path-local ordered tuple/list of such frames. `_Path.event` can remain a legacy single-event interface only for default mode; packet logic must not overwrite it repeatedly and lose earlier transitions. Full path.times/states/steps remain one trajectory. Expose packet first/last event times and ordered cell tuple separately, not a fake group event time.

Candidate selection may use min tangent time for safe ordinary advance, but near-terminal selection needs all relevant liquid polynomials from ONE common sampled midpoint, then strict isolated-root ordering. `u_i<l_j` establishes numerical surrogate order even if gap<time_absolute_s. Every candidate interval must be on its decreasing branch and root containment must be rechecked. Canonical cell index never breaks an overlapping interval tie. Actual exact common roots can delegate to separately admitted group handling or remain explicit unsupported; do not simulate zero-duration sequential panels.

## Current traps and required changes

1. `continue_after_event`725–750 currently forces common time before the next predicted event and rejects when spacing<=timegate. Packet mode must instead process later events up to the already chosen common endpoint through fresh actual mixed-mode RHS. Do not carry the original all-wet polynomial forward after the first switch. Legacy behavior stays unchanged.
2. `normal(...,check_remaining)` invokes the check at RK stages. If a stage indicates an event would be crossed, abort/reject that speculative RK panel and return to the last accepted state to localize it. Never install an event at an internal RK stage or retain partial quadrature from the aborted panel. Count evaluations/rejections/wall consumed by the aborted attempt.
3. Proposal795–809 checks a single event_cell and returns immediately after `continue_after_event`. Packet initial identity should bind the first strictly selected event; later frames bind their own mode/source/clock. Once one packet proposal is formed, refinements must match the entire ordered cell sequence and final modes, not merely first or last event.
4. Single comparison around815–890 uses one event_state/observation and pressure snapshot. Packet comparison must compare corresponding frames' complete N/E/T/P/stretch arrays and each time bound, then take maxima over ALL frames plus common endpoint. Preserve both original point-pressure and selected paired-pressure diagnostics for each frame. Same inventory zeros at common time cannot excuse a wrong intermediate event state or reversed mode history.
5. Commit around899–948 currently applies only `event.correction` when `step is event.terminal_panel`, and appends one event. Build a one-to-one panel→frame map, reject duplicate panel association, apply each matching correction once, and run every original-initial prefix N/E/component/mechanical check across ALL steps. Extend global events/corrections only after whole packet audit succeeds. No partially committed packet if a later frame fails.
6. Spine cache binding764–772 includes event_cell and interfaces. Keep cached ordinary edges only under the original immutable operator/mode/state binding. Do not reuse all-wet edges after a dry switch; never cache terminal/correction evidence as an ordinary edge. Common horizon changes invalidate relevant spine exactly as before.

## Clocks, refinement and termination

Each event uses its own actual represented start/end, affine coefficients, local gross evaporation and correction budget. Positive residual remains its own clock-rounding account; do not borrow another cell's evaporation or combine corrections to pass. Keep per-panel full mechanical vector and component energy terms, without extra latent/D heat.

For a near event after a switch, a representable positive midpoint and endpoint must still exist. If they do not, return structured unresolvable-order/clock failure; no epsilon shift. Interval overlap can be narrowed by bounded exact polynomial bisections, but these are numerical surrogate intervals only. If root order changes across refinement, further refinement may resolve it; otherwise fail without pretending equivalence of two permutations.

Use the same original common time for both compared paths. Compare all event times by per-frame absolute difference plus original clock bounds; do not reinterpret time_absolute as required spacing. Maintain two consecutive full-packet passes AND independent finer approach with actual distinct grids. A path may contain more events before common time than another; treat this as unmatched packet and refine/replan under a recorded common horizon, never drop extra events from comparison. Ensure common time lies after the last matched event and before any unresolved boundary/program conflict.

Maximum packet size is bounded by initially wet cell count and each cell may transition once under no-nucleation mode. Combined original attempted-panel/evaluation/wall/rejection/refinement budgets apply to all members and discarded paths. This gives termination without a new unbounded while-loop. Record reasons for membership/order/horizon changes.

## Evidence/auditor integration

Keep old single-event record schema/default path intact. Packet record needs each frame's terminal panel index, input/raw/corrected state and mode transition, individual affine clock+positive evaporation, correction or exactzero None, ordered polynomial root evidence, all pair comparisons and common endpoint. `event_record` must rederive panel/state/correction association and modes using explicit actual operator, then original cumulative conservation and source contracts. Service continuation restores complete packet history once; it cannot flatten records into duplicate shared panels or assume cell-index ordering.

## Required independent no-EOS tests before actual4cell probe

- Two analytically distinct roots separated by less than original timegate; stable order, full packet accepted without shared-time finite deletion.
- Equal initial tangent estimates whose affine roots separate after normal accepted advance.
- A first mode switch changes the second sink: fresh mixed RHS root versus stale all-wet prediction.
- Same final common state but wrong intermediate E or reversed event order; comparison rejects.
- Second-event local fraction/clock/source failure: previous global prefix preserved, no first-event partial commit; all costs retained.
- Two-event corrections on distinct panels: exact original-initial N/E ledger totals and mechanical/component residuals, no duplicate corrections.
- Stage-triggered impending next event: aborted RK trial contributes no ledger/state but contributes work counters.
- Cancellation before/between/after proposal frames, resume after accepted packet with cumulative budgets; legacy single tests unchanged.
- Unrepresentable inter-event panel, overlapping non-exact roots, event/program-node collision and unmatched packet membership: explicit failure.

Then one bounded actual4cell original initial case short-event window with unchanged gates/sources, using existing before-assert failure serialization and independent prefix audit. Success is empirical numerical packet acceptance; neither true physical simultaneity nor spatial convergence follows. Only after that should the4/8 longer-time spatial sequence proceed.

## First actual code review (implementation in progress)

Two HIGH issues sent to author/root immediately:

- continue_packet789–800 calls normal without a stage checker. This drops the accelerating-remaining-event detection present in the legacy continue_after_event branch. Wire a packet-specific stage replan through normal's existing pending-exception boundary521–566. Never terminalize an internal stage. If integrate had already accepted substeps before detecting the issue, either retain those complete accepted substeps in the speculative path or deliberately discard them and retry from the saved segment start; retain all consumed counters. A special replan must not swallow source/domain/cancellation errors.
- Acceptance1178–1179 updates only packet_frames[0] with real common time/previous/coarse/differences. Other events retain construction defaults (common time=self, previous=self, zero differences), misrepresenting accepted diagnostics. Update all corresponding frames from their actual comparisons and coarse/previous frame histories, or move acceptance diagnostics into an explicit packet-level object and prevent those unverified event fields from being presented as meaningful. Do not write packet maximum into a field claiming a member-specific difference without labeling it.

Positive findings: comparison978–993 iterates matching event-cell sequences and checks final modes, invokes original full-state comparison per frame, and aggregates maxima; commit maps terminal panel identity to corrections and refuses duplicate panel identity. These are the right structures. Numerical root selection640–674 re-localizes all wet affine polynomials from a shared actual midpoint and requires strict interval separation; it does not use timegate as minimum root distance.

Requested test additions beyond the current11 tests: stage-driven accelerating later event with an accepted prefix before replan; per-event accepted common/previous/coarse/difference metadata on second and later events; malformed/mismatched packet metadata audit; no duplicated cost/ledger when stage replan discards a partial segment. Existing close-event test checks mixed RHS and correct endpoint values but does not detect fake metadata or exercise the missing stage check.

Review remains pending those fixes; no EOS or tests executed by this reviewer.
