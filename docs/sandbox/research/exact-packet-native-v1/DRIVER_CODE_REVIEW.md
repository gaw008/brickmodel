# Exact packet driver preliminary code review

Candidate is still being edited; no final source hash approval. No repository edits or EOS. One bounded pure instrumented cancellation reproduction was run.

[HIGH] Ordinary callback guard status is lost through integrate_exact.
File: exact_depletion_integration.py, ordinary/observe/guard.

The driver's _Stop subclasses IntegrationError. When cancellation or outer wall expiry happens after an actual ordinary callback, integrate_exact converts it to numerical_failure. ordinary then wraps run.status and cannot recover cancellation/resource classification. Actual existing setup with cancel=lambda:len(calls)>=3 returns numerical_failure/cancel_requested, three calls and zero accepted steps. Preserve the outer stop type/status alongside the replan flag, then charge and retain returned local prefix before propagating it. Add post-callback cancellation and wall regressions. Outer DomainExit paths should also retain domain_exit by exception type.

[HIGH] Original water-mass admission deferred until a terminal occurs.
File: exact_depletion_integration.py, integrate_exact_depletion initial validation.

Legacy depletion_integration rejects mismatched roundoff molar mass against actual chemical reference before observation. This driver checks only inside execute_exact_terminal. Ordinary work runs first and a horizon ending before depletion can complete under mismatched original roundoff policy. Restore the pre-observation exact mass guard and add a short-horizon zero-call mismatch regression.

Other preliminary inspection: source-bound exact views, complete frame sequence/common modes, paired pressure helper unwrapping and counters, original global N/E/component/stretch ledger and correction sums, candidate-only mode transitions, two-pass plus independently halved controls/grid, and research-only result subtype are present. Final review of fixes, pure tests, source freeze and remaining control-flow behavior is pending.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 2 | warn |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: WARNING — close guard/status gaps before final approval.

## Reviewed repair snapshot

Inspected source SHA256 39da99110b28ca0cbbf241c9008f825a6851c2cd02a22871ece5e15273a2b9e4 and tests 568eeeb07ea5c781733c9508f0a770a803c37fc01348cd20ba3ddde195adfbe8. Actual tests14.log: 15 passed in 5.92 s. Author freeze confirmation is still pending; approval below applies only to these bytes.

Both HIGH findings are closed. The ordinary callback catches and preserves the original outer _Stop, charges integrate_exact costs and appends its accepted local prefix, then rethrows the original classification. Initial wrong-mass policy now fails before any callback, including a horizon without terminal events. Tests cover callback-triggered cancellation/wall expiry and no-terminal mass rejection. Actual DomainExit also receives its own status instead of generic failure.

Full review scope: original state energy identity and complete paired-pressure boxes are checked; exact adapter pre/post identity protects actual calls. Every terminal mode change additionally preserves all non-mode physical/source content through the reviewed executor. Global acceptance reconstructs N/E, component sums and represented/exact stretch accounting from original initial state over every prospective accepted prefix, applies each paired phase correction once at its own terminal ledger, reconstructs all cumulative correction totals, and mutates global lists/operator/totals only after those checks. Ordinary stopped prefixes are handled separately from speculative packet failure. Speculative failures retain paths/refinements/terminal attempts and costs without publishing mode changes.

Comparison checks complete event sequence and common modes, evaluates each full corresponding event state and shared common state, retains all six original gates and independent point-pressure bounds, and passes actual underlying WPT operators/states/inverses to the reviewed optional pressure helper. Paired endpoint attempted/completed counts remain separate from host evaluations. Two consecutive terminal refinement passes are followed by an actual separately computed approach with both cap and safe fraction halved and distinct ordinary endpoint grids. Per-frame coarse/previous/common metadata and packet maxima remain explicit. Exact-zero polynomial endpoints correctly have zero surrogate clock uncertainty; other roots retain both enclosure widths.

Global panel/rejection costs include discarded ordinary trials, terminal predictors and terminal panels; one outer wall deadline is propagated to callees, with separate pressure endpoint guards. Cooperative guards cannot interrupt an active native call; external watchdog remains necessary. No ordinary spine reuse is claimed. Current ordered continuation handles further events to fixed common time and refuses unsupported root/node cases; it does not implement the legacy nonordered common-horizon reduction/restart branch. The explicit exact result is separate from legacy float records/checkpoints and makes no resume claim.

Pure tests use real numerical chain/strict exact adapters with instrumented native dispatch. Pressure test proves wiring, not an actual physical certificate; real helper has separate evidence. No complete native exact packet result has been observed in this review, and no material qualification follows from code approval.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE stated snapshot for bounded exact ordered research core; require freeze byte match before application.

## Final freeze review: panel budget and pre-first-event grid

Final frozen source SHA256 be323c820fe9f0c0981bb3bc7b4db817c8931c2501e704e394ae85a4c815a16b; test 3e96e5a57c69076183daf74da2c4d80bd713c860d1ed698fc43f42312bb790f2. Read actual tests18.log: 16 passed in 5.92 s. This supersedes the 39da snapshot approval, which did not detect the two subsequent findings from the other reviewer and must not serve as overall final approval.

Original legacy depletion driver charges accepted ordinary panels, interrupted stage replans and terminal panel attempts (source guard and normal accumulation inspected). Final charged_panels now uses exactly ordinary_panels + stage_replans + terminal_attempts. The same count controls global guard, callee remaining maximum_steps and one-panel terminal admission. Rejected trials and predictor attempts remain separately recorded and no longer consume this original panel budget; original rejection and wall limits still apply. New regression forces ordinary rejections under maximum_steps=1 and demonstrates one accepted panel is retained, with rejected trials counted separately. No extra physical tolerance or enlarged original panel limit is introduced.

Path approach_grid now extends only while path.frames is empty. Thus the independent mesh distinction must arise before the first terminal; different post-event continuation grids cannot make identical terminal approaches appear independently refined. Existing distinct-control/grid test reads this narrowed recorded grid. Later ordinary paths remain fully represented in times/states/ledgers and costs. Source/guard/classification/atomic ledger logic reviewed previously remains intact.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE final be323c82 freeze for exact ordered research core. Code approval is not proof of a completed native four-cell packet, legacy codec/resume or material validation. No EOS or repeated tests run in this final review.
