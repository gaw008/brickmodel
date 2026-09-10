# Independent Python review: source net prefix arithmetic

Final disposition: **APPROVE**. All findings raised by this reviewer are resolved in the current source. No outstanding CRITICAL/HIGH issue was found in the reviewed arithmetic, policy binding, typed evidence checks, or shared schema changes. This reviewer edited only this temporary review directory and made no production edits or commits.

Scope: the `affine_integral_value`, `affine_integral`, and `affine_update` extraction and old wrapper in `exact_terminal_panel.py`; `source_net_prefix.py`; associated new tests; and the parent's resulting common `source_net_panel.py` face/array guards. Baseline is `1fd9e87`.

## Resolved findings with preserved RED evidence

[HIGH] A saved prefix could silently change its original numerical policy

File: `src/sludge_sandbox/source_net_prefix.py`, `SourcePrefix.policy` and `check`.

Issue: the result retained the caller's policy object, then rebuilt itself from the same current policy. Mutating a tolerance to another valid positive value or replacing only the policy let `check()` accept relabeled original evidence. Policy validation alone only rejected invalid policies; it did not preserve the original policy.

Fix verified: the result now retains an independent tuple of every original policy field and value, compares it with exact scalar types before rebuilding, and includes the binding in reconstructed record comparison. Caller mutation, result-policy mutation, replacing the policy, and binding type substitutions are rejected. No tolerance was loosened by the repair.

[HIGH] Boolean face identifiers could enter integer source diagnostics

File: `src/sludge_sandbox/source_net_panel.py`, shared face incidence validation.

Issue: `face_id=True` compared equal to face index 1 and was accepted and retained in a prefix's diagnostic record. The previous equality-only adjacency checks likewise admitted boolean aliases.

Fix verified: the shared source-panel entry now requires exact integer face IDs and exact `int` or `None` adjacency types with correct values. The provider removed its duplicate guard so both old panel callers and new prefix callers share this check.

[MEDIUM] Interior source-state array dtype changes escaped saved-content checks

File: `src/sludge_sandbox/source_net_panel.py`, saved sample validation.

Issue: replacing either interior state array with equal-valued `float32` data left the `.tolist()` digest unchanged, and the prefix used only the first state for numerical updating. Both altered interior arrays were therefore accepted. The observed numbers were unchanged; this was an input-schema and saved-evidence type gap, not an observed conservation error.

Fix verified: both state arrays and all four rate arrays now require exact ndarray class, float64 dtype, and finite values at both sample times; existing shape requirements remain. All twelve independent state/rate/time combinations reject the changed dtype.

## Actual tests and source identity

- `red01.log` / `red01.xml`: four actual failures, all `DID NOT RAISE`, in 0.15 seconds: caller policy mutation, saved policy mutation, replacement of only the policy, and boolean face ID. The original probes are preserved in `test_policy_binding01.py`. `red01-freeze.json` and saved source copies identify the pre-policy-binding source; the provider separately confirmed SHA `0cc7d2d96da5cfab4a1e4fb3450922f018b615357173eefeba6811f80ea8ca58` as its pre-policy-binding bytes.
- `array-red01.log` / `array-red01.xml`: **2 failed, 10 passed**, in 0.18 seconds. Both failures were the equal-valued float32 interior state mutations described above.
- `tamper01.log` / `tamper01.xml`: **16 passed** in 0.23 seconds. These independently check forged exact aggregate residuals, typed scalar substitutions, policy binding, qualification changes, and that shifting internal-energy reference below zero does not introduce an energy positivity gate.
- Final complete independent adverse run: `final-review.log` / `final-review.xml`: **32 tests, 0 failures, 0 errors, 0 skipped, 0.249 seconds**. The boolean ID probe now permits rejection during panel construction because the repair correctly moved rejection earlier; its original RED form remains preserved.
- `FINAL.json` records final source/test hashes and actual XML counts. Final source SHA values:
  - `exact_terminal_panel.py`: `fa4323a190d91b47509458c7c1e46145dd6d8363bb4d883c5b23becc27afe932`
  - `source_net_panel.py`: `c728f0749252bc9a565612cb1b7601139108e88fccecd43af7df699873300918`
  - `source_net_prefix.py`: `8bcaef378eef0c35a08bdcf39f01b06ded8bf9283981f251935e89504d51d5e0`
- Independently read, but did not rerun, the parent's actual XML: pre-extraction 6/0/0/0, post-extraction 30/0/0/0, final shared-panel/prefix 55/0/0/0. XML SHA values and times are in `parent-xml-read.json`. The supplied regression compares thirteen full old result/error records to baseline, including large exact origin, mechanical and gas interior minima, selected/competing endpoint zero, state rounding, and integral overflow/underflow.
- All seven reviewed current source/test files parsed with `ast.parse`; `git diff --check` passed. `ruff`, `mypy`, `pylint`, `black`, and `bandit` are unavailable in the configured Python environment; their execution is not claimed. `scan01.json` records availability and source identity.

## Scope and remaining scientific boundaries

The exact integral helper accepts rational diagnostics without a float roundtrip. The array helper projects each integral once; state updating sums represented exchanges exactly before the final projection. The old wrapper still applies its original budgets; the new prefix separately bounds integral, state-only, and full inventory/energy residuals. The current aggregate audit also retains and checks cumulative exact-integral exchanges separately from represented exchanges; this closes the cumulative omission found by the other reviewer.

Checks rebuild derived records and reject altered types and contents. They do not recurse through an audit-building loop. Raw state and ledger arrays are rebuilt through the existing immutable snapshot constructors. Positive-initial inventory remains mandatory; tangent or endpoint zero has only a numerical-boundary label, with no physical event, writeback, wet-state inversion, dry continuation, or material qualification permission. Negative internal energy remains valid under a changed reference. The prefix keeps original face decomposition and liquid projection diagnostics, checks known diagnostic classes, and reports direction reversals without treating that diagnostic as donor-consistency proof.

No EOS call, source dynamics recomputation, external service, or physical event was needed by the independent probes. This review is not an external expert certification or evidence that the full wet-to-fired model is complete.

## Final installation evidence-script followup

Statically reviewed `/private/tmp/brick-source-net-prefix-v1/root/check_install.py` against the prior committed `docs/sandbox/research/source-net-roots-v1/check_install.py`. **APPROVE**; no blocking finding. A programmatic exact-text comparison confirms that the only changes select the first three path arguments and parse a fourth integer argument as the expected JUnit test count, then compare the XML count to that argument instead of literal 123. File matching, recorded SHA values, installed-location check, and zero failure/error/skipped requirements are unchanged. This stage calls it with expected count **131**.

Current script SHA is `eb67da83c7e00b9583561d55e10839211fa6a7ff02fa92a928b6e238085f3840`; previous SHA is `7fa4f5b866184e7ced453d0af4b0c127255ae1d8a3d5abb264df9108b823291a`. The script parsed with `ast.parse`; it was not executed by this reviewer. `install-script-review.json` records these values and the exact-diff verification. Final installation execution and its actual 131-test XML remain parent-owned evidence; a still-running installation test was not treated as passed in this followup.
