# Persistent ordinary source continuation: implemented interface

## Public calls

- `save_source_trajectory(session, output) -> dict`: creates a new local packet and permanently suspends the original live session. Only the actual issued clean `paused` result/checkpoint identity, closed managed lease, unchanged costs, and explicit `RESUME_PROFILE` are accepted. The returned summary has `status='suspended_offline'`, `disposition='saved_and_live_session_suspended'`, `source_resume_authorized=True`, and the numeric checkpoint SHA. Historical study resume, material qualification, and full firing-cycle flags remain false.
- `read_source_trajectory_checkpoint(directory) -> SourceTrajectoryCheckpointRecord`: passive validation of the entire packet, original parent, current runtime/assets, numeric replay, source observation/callback/journal correspondence, original reconstruction request, returned result, and cumulative balances. It constructs no provider. Reading does not consume or renew the single-use restore claim.
- `restore_source_trajectory(saved_directory, output, *, cancel=None, managed_execution=False) -> SourceTrajectorySession`: atomically consumes the packet's local `.restore-attempt` claim before validation/reconstruction; restores existing event bytes/count/byte budget and saved source captures; uses the existing reconstruction path to build real providers once; installs the admitted ordinary checkpoint and original cumulative cost. The returned session resumes through its existing `advance` method. It performs no new initial energy computation or numerical initial probe.

The session's underlying source study remains a passive parent. Only the ordinary numerical segment has continuation authority. Serialized data never instantiate a lease or a provider, and old same-object diagnostic flags retain their original-process meaning.

## Cost and lifecycle boundaries

Charged work is S + A: prior measured work and online pause, plus new reading, auditing, rebuilding, copying, saving, and publication work. The original 180-second ordinary policy and source lifetime limits remain unchanged. Offline D is reported separately; a backwards civil clock produces `clock_discontinuity` without granting credit or inventing elapsed time. A new managed lease is acquired only inside `advance` and is closed before pausing/returning.

Saving writes `FINALIZING.json` before expensive work. Readers reject the packet while this sentinel exists, including a process death after manifest publication. The old session is closed before publication, cancellation is checked before the save and before sealing, and the sentinel is the final publication operation. A declared conservative one-second allowance covers the final publication tail; it is not reported as measured elapsed time. The elapsed guard must pass before sealing. A caught save failure leaves the old session closed and unfinished evidence plus cost/count details; cleanup failure is secondary to the original exception.

Restore uses an exclusive local directory claim. An interrupted or failed attempt cannot retry from that same packet. This is a local managed-directory integrity rule, not cryptographic source authentication or global clone-resistant authorization. The package includes local private source assets and is not a public export format.

## Packet and validation

The packet preserves the original parent tree and source assets, exact old event files/ordinals, a closed numeric checkpoint codec, and a source study containing the old contexts/captures in original positions. The numeric codec passively replays all old callbacks and rejected/accepted arithmetic. Source validation additionally binds exact states/times/Rates/failures and each raw event to that callback order; all original N/U cumulative balances and policies are recomputed. Every reconstruction event binds the original segment start/end and chosen step sizes. The last `ordinary_segment_returned` event is compared in full against the reconstructed result.

Raw graph comparison is type-sensitive, preserves sharing through memoized resolution/comparison, and has explicit depth/work limits. JSON duplicate fields/nonfinite values, asset/runtime changes, altered evidence, missing files, unfinished finalization, spent budgets, and consumed claims fail closed before provider construction. Managed audit copying has the same bounded shared-container handling.

## Verification and limits

The actual manufactured source fixture uses existing SourceWetStorage/SourceWetColumn/ExactSourceColumn implementations and the existing explicit liquid property seam. It does not execute native EOS. The pause/save/read/rebuild/continue test compares all accepted states, exact clocks, callback observations, numerical counters, and balances against the continuous path, excluding measured wall time; original journal bytes are retained.

- `final02.xml/log`: 19 passed, XML 85.228 s / pytest 85.23 s. This includes the real manufactured roundtrip and initial reconstruction, source-order, asset, budget, single-use claim, offline-clock, save cancellation/finalization, and raw-graph checks.
- The final owned-audit memo fix adds one test. `final03.xml/log`: 3 affected controls passed, XML 0.253 s / pytest 0.26 s; 17 deselected. The earlier full batch is retained and was not relabeled as a final 20-test full run.
- The final source differs after final03 only by public input annotations. Independent review owns the original raw shape, shared graph, audit-copy, and cleanup probes.
- `ruff`, `mypy`, `pylint`, and `black` are unavailable in the selected test environment. No installation, native run, commit, or repository changes outside the three owned files were performed by this implementation agent.

Commands used the existing `/private/tmp/brick-water-backend-probe/venv/bin/python`, `PYTHONPATH=src`, and the `SOURCE_RESUME_TEST_PACKET` cache of the actual first manufactured packet. Root will perform the final source/installed regression using a newly created packet after the final runtime manifest is pinned.
