# Installed source-run acceptance, registered before execution

This is an execution-service slice under the unchanged Goal contract. It does
not complete a sludge firing cycle or validate manufactured geometry/transport.
Baseline before the slice: `a493619`. Actual HEOS execution has not yet occurred
when this plan is first written.

The single native acceptance run uses
`data/sandbox/cases/source-multicell-heos-v1.json`, explicit assets root, and the
noneditable installed package. The default input SHA-256 is
`323cdc6ebbd866c81e87ac1227155357253f0b05f2384c55fadead85218c2dc5`.
No parameter or verification tolerance changes are authorized to obtain a
preferred event result.

The source configuration controls the original 3-cell initial inventories,
temperature, independent per-cell volume declarations, liquid transport,
integration/event/roundoff policies, source molar-mass rule, and actual-probe
horizon rule. It caps 16 callbacks per wet trial, 24 per dry path, 97 total RHS
starts, 16 additional wet pressure requests, and 510 s of cooperative work.
Run the real owned child through `supervise source-run`, with a 570 s outer
process limit and 10 s cooperative grace. The supervisor may terminate and reap
its own child; an interrupted attempt remains an attempt without a fake return.

Required service acceptance:

1. Configuration and all 17 local assets are verified before provider creation;
   only the needed local hierarchy is copied into the run. Publisher sources
   remain private, and the run bundle is not a public redistribution artifact.
2. The installed source/configuration files match the frozen working tree.
   The approved HEOS kernel and manifest retain their original bytes. The
   observing Python wrapper has a new, explicitly recorded implementation hash.
3. Four actual HEOS wrapper starts, four kernel/anchor returns and four complete
   wrapper returns; three initial U starts/returns; no test backend replacement.
   These counters do not count internal EOS updates or all native operations.
4. Actual probe, seed, proposal, approach, root refinement, two dry candidates,
   shared wet/dry pressure comparison run through installed library APIs. No
   loading executable research scripts or monkeypatching the production run.
5. Every actual source start/return and additional water request is durably
   recorded; returned stages survive subsequent failure. Check complete capture
   counts, identities, original policy fields and all three cells. The original
   numerical event decision and pressure gates are reported without alteration.
6. A completed computation is not sufficient: its full SourceStudyRecord must
   pass the existing passive schema/association/ledger audit and shared read_run
   checks. Inspect a selected original capture and complete transition gates via
   the installed CLI. Finalization and inspection must not add physical calls.
7. A valid comparison with a false acceptance gate remains a valid software
   execution result with the original false gate. Unexpected failures, limits,
   unfinished comparisons and record-publication errors are preserved; no
   automatic retries or revised physics are used to turn them into success.

The manufactured seam tests are separate from this native acceptance. They
exercise control flow and cancellation/I/O failures; they do not supply external
material validation. Rebuilding a frozen case is replay, not checkpoint resume.
Source-study continuation, UI integration, raw-sludge chemical closure,
sintering/cooling, the three public mechanism holdouts, full cycles and
multigeneration source-model search remain unfinished Goal requirements.
