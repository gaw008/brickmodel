# Independent continuation code review

Reviewed frozen driver `5c06f392fa8415a8b6d57e9605e04074052cc9a2e04225a5df9ec35b8a2028a2`, admission `a3819fba56f7bdf8009be1f8c7a06449f7e6c2750e663c2063ecbf56103c7432`, and portable test `f17531439b8869a9efdebac6f829a210b630e14a2824ba107f22d3f49f941141`. Compared driver against preserved `be323c820fe9f0c0981bb3bc7b4db817c8931c2501e704e394ae85a4c815a16b`; read admission, complete tests, surrounding commit/refinement/observation/resource paths, strict codec and comparison grouping. Repository edits observed at review time were unrelated documentation only; no repository source was changed by this reviewer.

No blocking issue identified in this bounded core change. Independent pure execution of the nine portable tests through the coherent temporary preload harness passed: **9 passed in 8.86 s**. No EOS/native execution or installation was performed.

Admission reparses immutable parent bytes, checks their externally supplied SHA, requires exact current execution runtime before/after admission, and freshly runs all four audits against original state/time/policies and actual original operator. All reports must reference the same record. Restore supplies actual mode operators while retaining historical observations as evidence projections. This does not reuse an earlier partial approval as authority. Caller-supplied authoritative parent hashes still require a trustworthy application/run store; this core API neither authenticates arbitrary editable telemetry nor implements service lineage/concurrent-claim fencing.

The resumed driver retains original initial/end/policies, complete accepted and discarded histories, correction totals, all cumulative counters, restored terminal-ledger aliases and historical component schema. New commits recompute original-initial cumulative N/E/component/stretch constraints. No second history merge or correction charge is introduced. Original panel charging remains ordinary panels + replans + terminal attempts. Admission and resumed active time are added to prior elapsed with outward float rounding; ordinary/terminal subcalls receive remaining allowances. An exhausted resource parent returns its original reason without new physics calls. Cancelled parents that have exhausted credits stop at the normal guard. Invalid admission raises before new trajectory work.

The commit observer receives only an immutable count/count/exact-time tuple after complete publication; an exception retains the published prefix and reports failure. Default None path changes no numerical controls; the baseline comparison excludes only elapsed_seconds throughout nested evidence. Restarted adaptive work is explicitly recomputed and debited, not claimed identical to uninterrupted adaptation. Comparison grouping starts a new group at each genuine coarse reference, so retained interrupted refinement histories do not masquerade as the fresh group's coarse anchor.

Pure tests use instrumented typed host shells and patch geometry/observation qualification plus runtime identity, while the four numerical audits themselves run. Their success does not establish native water behavior or material validity. Same-new-runtime native cancel/resume remains a separate experiment. The prospective runner has a separate serialization blocker reported to its owner; this approval does not approve that runner's current bytes.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded exact core continuation and portable tests; no service/legacy or cross-version execution admission implied.
