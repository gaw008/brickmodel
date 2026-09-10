# Independent Python review: actually evaluated source prefix trial

Final disposition: **APPROVE**. No unresolved CRITICAL/HIGH issue remains in the reviewed frozen bytes. This reviewer changed only temporary review files, performed no native/HEOS run or installation, and made no production edits or commits.

Baseline: `cc94ecb`. Reviewed the exact Euler helper extraction in `exact_integration.py`, the new `source_prefix_trial.py`, the associated tests, and the final failure/recovery amendments. Final source hashes:

- `exact_integration.py`: `d65b6844141ff73f4ad23cee5950e4548062646072195b862e8bfb5125af4409`
- `source_prefix_trial.py`: `d092a37fe69be5e5cae968f7c7967233ea8cdd4837428bf6236ddbed3c204b99`
- Trial tests: `4db4131fa8fb1d9ee7b85d9b32d427aa58cdaf9019ddef6fe7289bcb24e6d1ac`

`FINAL.json` binds all six implementation/test/fixture files and the actual independent test XML.

## Resolved findings and actual RED evidence

[HIGH] Saved reference ledgers could be altered without invalidating a successful trial

Issue: endpoint/status/length checks did not connect intermediate reference states and ledgers to retained callbacks. Changing the first reference left-face integral by **+1 J** still passed `.check()`.

Fix verified: the original `integrate_exact` now passively replays the retained RHS captures, checks every requested state and exact time, and compares the complete reference result except nondeterministic elapsed time. It does not rerun source physics. The original numerical controller, accepted/rejected gates and ledgers are reused, not reimplemented. `trial-red01.log/xml` preserves this actual failure.

[MEDIUM] A result could be relabeled with an invented outcome

Issue: replacing a successful result with `status='unsupported'` and an invented reason bypassed its success-only checks and passed validation.

Fix verified: original outcome and control tuples are retained and compared with exact types. The second actual failure in `trial-red01.log/xml` demonstrates the pre-fix behavior.

[HIGH] NaN energy could produce an apparently zero normalized discrepancy

Issue: after a state energy array was mutated to NaN, `max(0.0, nan)` retained the amount difference, so the final finite-result check accepted discrepancy zero. Both prefix-side and reference-side mutations were reproduced.

Fix verified: the four comparison arrays must be actual nonempty finite float64 ndarrays before subtraction. State arguments now have concrete type annotations. `discrepancy-red01.log/xml` preserves **2 failures in 0.14 seconds**.

[HIGH] A failed terminal callback's attempted state was not bound

Issue: after a real terminal `DomainExit`, replacing only that failed capture's state with inventories increased by 1 still passed `.check()` because it had no successful evaluation binding.

Fix verified: every attempted callback retains an immutable typed input tuple and original failure-kind/message tuple. Known initial/midpoint/terminal inputs are also checked against the actual computation regardless of overall outcome. `failed-capture-red01.log/xml` preserves **1 failure in 0.73 seconds**.

[MEDIUM] Empty exception messages made genuine failure records uncheckable

Issue: `DomainExit()`, `IntegrationError()` and `ValueError()` were retained correctly, but the check treated an empty failure string as no failure.

Fix verified: failure occurrence is distinguished by its bound kind and the presence of a string, allowing an empty message while distinguishing it from `None`. `empty-failure-red01.log/xml` preserves **3 failures in 0.59 seconds**.

The parent separately found that a reference which recovered from a rejected `DomainExit` was incorrectly rejected by the trial's all-successful-captures check. The final code retains explicit failure kinds, allows reference-internal DomainExit captures only within a completed original reference, and re-raises those saved DomainExit values during passive replay so the original rejection/retry sequence must match. Other numerical failures or resource stops are not promoted into recovery. This reviewer read that repair and the provider's actual regression log, but did not duplicate the parent's recovered-reference experiment.

## Actual independent verification

- `euler01.xml`: **11 tests, 0 failures/errors/skips, 0.050 seconds**. Covers exact positive Fraction duration, unchanged nonzero-product underflow behavior, overflow and rejection classifications, zero versus negative inventory, negative reference energy, input immutability, existing state/rate/policy subclasses, mechanical scales/positivity, and original state-roundoff gates. The helper bytes remained unchanged afterwards.
- `trial-final.xml`: **14 tests, 0 failures/errors/skips, 12.948 seconds** on the final `d092a37...` source. This is the combined final rerun of all existing independent trial probes after the repairs. Together with the unchanged helper suite this review has **25 distinct independent passing cases**.
- `trial-red01.xml` initially had **2 failed and 3 passed in 5.02 seconds**. The three TypeError/AttributeError/OverflowError probes already passed because the provider had repaired callback failure retention before that actual invocation. Those were not reported as historical RED. The final probe additionally checks the retained exception type.
- `binding-red01.xml` actually contains **3 passing tests in 5.82 seconds**: terminal and reference captures cannot drop their successful binding. Despite its early filename, this file is not failure evidence; the repair landed before execution.
- Parent-produced XML was independently read, not rerun: baseline **17 tests in 4.798 seconds**, helper/legacy/original suite **27 in 4.896 seconds**, both without failures/errors/skips. `parent-legacy-read.json` records exact hashes/counts.
- The frozen pre-extraction fixture has **12 full output/callback records**, 163855 bytes, SHA `80cfc4654847fe30655bcc4094f6574d29981f111e19935c47bb7229e65576de`. Only elapsed wall timing is omitted from deterministic legacy comparisons. A fixture named `energy_roundoff` completes under its exact arithmetic; its name is not evidence of a failed numerical gate.
- The provider's final `recovery-final-tests.log` was read: **31 passed in 29.46 seconds**. This is provider-run evidence and is not added to the independent count.
- All reviewed final Python files parsed with `ast.parse`, and `git diff --check` passed. `ruff`, `mypy`, `pylint`, `black` and `bandit` are unavailable in the configured environment; their execution is not claimed. Initial availability is recorded in `scan01.json`.

## Behavior and limits reviewed

The Euler helper preserves the original `rates.derivatives` → `_scaled` → `_updated` arithmetic and original rejection classifications. It accepts the same existing validated class subclasses, requires a positive actual Fraction duration, and revalidates policy values/required mechanical scales. It deliberately preserves the original product-underflow behavior instead of importing the stricter affine integral projection policy.

The trial copies and binds the original caller policy, records source-call attempts before dispatch, retains actual outputs before downstream validation, counts failed attempts, and checks cancellation/deadline before and after physical observation. Only remaining wall resource is reduced for the actual reference; numerical tolerances and scales remain unchanged. Successful trial checks include final bookkeeping and are followed by the outer deadline guard. Passive replay is a numerical evidence check and does not certify the historical execution cost.

Successful output requires genuinely evaluated initial, Euler midpoint and prefix terminal source observations plus a completed original reference over the identical exact interval. Direct amount/U discrepancy is not divided by 3. Terminal temperature and pressure bounds are taken from actual `SourceWetInverse`/its point, including the source pressure error, rather than inferred from unpacking or a bare EOS value. Failed or resource-limited reference prefixes remain retained evidence, not a successful comparison.

All tests here use pure arithmetic or the actual source host with explicitly manufactured water/transport fixtures. No HEOS/native evaluation was performed by this reviewer. Positive numerical trial consistency does not establish event-time accuracy, dry/rewetting continuation, transport correction permission, real-material qualification or completion of the full Goal.
