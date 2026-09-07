# v3 script and preregistration delta review

Verdict: APPROVE the frozen experiment-script delta, subject to completion of the root's source-guard and applied/installed identity checks. No EOS, test, probe or script import executed by this reviewer. No source/script/PLAN edits performed in this review.

Compared all five actual /private/tmp/brick-reacting-wet-v3 scripts against v2. callback.py, depletion.py, run.py and compare.py are byte-identical. fixture.py has only three added lines: import NestedApproachPolicy, then attach nested_approach with maximum_step_s equal to that run's existing ordinary policy maximum and reuse_ordinary_spine=True. No physical construction, initial state, source/error value, inverse policy, amount/time/energy/pressure gate, correction policy or resource cap changes.

Final fixture SHA: `b85f1d55460b65b64ff4ecade268b9b2f2168a87271c472b3065ddb682f0c531`.
Other unchanged script hashes:

- callback.py `a84b7ea5dd7adfd4838595d41ddbe149482442a1b31391de56c99f8f907faae6`
- depletion.py `141a90056e70c21318cc2b72615150a0d78827b77992e0b4444c93695d9891f4`
- run.py `dcc9ba014c8f642824f25662dc0ac39961f5580e0db85d367f7032bb7369e612`
- compare.py `b2f9385f489f3362f88bea79e21b8e9c40a3557a359a45945f8e20b687ede3c3`

Initial review found PLAN still pinned the old fixture hash. Root corrected that provenance mismatch before any execution; I reread and independently verified all five current file hashes against the updated prepared_script_sha256 map. No initial mismatch is presented as a successful check.

PLAN differs from v2 by experiment/baseline identification, the explicit nested strategy record, execution gate and corrected fixture hash. The prior pressure-bound numerical-change record and physical/error/gate settings remain. The nested record correctly states fixed ordinary cap, unchanged safe fraction, reusable ordinary prefix and uncached independent half-cap/half-safe comparison. Candidate SHA is 88a9e4f613a0b7cc2fa6c5543b3a5c9ce02c6203a5fc5cba5c8205e00682c8d9. The baseline commit labels the pre-application provenance; actual installed-vs-source identity checks are still needed to prove the executing module is the new candidate.

The unchanged callback remains a source/geometry/energy-binding check, not a trajectory success. The unchanged depletion script preserves returned failure data before assertions and still requires one real event, dry continuing A/B reaction, original prefix/correction gates and nonzero retained interface coefficient. Its encode helper handles added mapping diagnostics. The supervisor requires both complete status and exit zero, and the comparison preserves input hashes and failure output. No v1/v2 failed result is overwritten by this separate v3 directory.

Execute serially only after source guard and applied-code review: callback, inspect actual terminal result, first depletion, inspect, second depletion only if the first succeeds, then compare. Keep the original 120 s integration / 150 s supervisor / 500 panel limits. Runtime improvement and successful wet depletion remain unproven by this static review.

## Final candidate update

The final reviewed candidate is now `ab465ad7a1da9d39787afd7dd2c6dfc24e680936e9a6c99593b345ddbc49135a`, superseding the earlier 88a9e4f6 candidate. Late source-binding checks before independent verification, horizon reset and commit close a real four-case fault regression; actual combined XML is 20 passed, 5.828 s. See the appended Python review for exact scope and evidence. No physical or v3 fixture/script changes are involved.

V3 bounded execution is approved once PLAN's numerical_strategy candidate hash is updated to this final SHA and root confirms actual applied/installed byte identity and required regressions. The earlier source-guard prerequisite is now met by the reviewed six source/boundary cases within the 20-case result. This approval does not itself verify PLAN's pending hash update or installed runtime, and does not assert a native run has succeeded. Keep original serial execution order and budgets.
