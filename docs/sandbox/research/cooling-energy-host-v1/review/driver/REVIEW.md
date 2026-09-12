# Independent package-port and research-driver review

**APPROVE the bounded port and driver for the already registered, supervised experiment.** No unresolved CRITICAL/HIGH correctness issue was found within this scope. No trajectory or native `integrate` call was run by this reviewer. Full experiment completion and runtime gates remain untested by these unit/fake probes.

## Bound versions

| File | SHA256 |
| --- | --- |
| Ported storage | `d98d6dccff4e31895da642ffa170ecd208c60e6e55b27ac5e314c36ace3f4579` |
| Ported host | `3f23da5d4612004cdb5baa1b490fbd249c8e2f2554337dcddb14a8677953c8c9` |
| `run_validation.py` | `574a80ef01617045fc71beabf4234dc179201723d0f079398336ba8439db1f97` |
| `supervise.py` | `96f89838487e3733631f57a3bd04bcce81e8f294b5a6e6516e6a483b88ba1710` |
| `test_driver.py` | `2e2ddc141211109931db8a383d2a6e69524ee66acf0858656137413ae950917b` |
| `PREREGISTRATION.md` | `630c3c6586a63e8ee21a60b215d2e3d1bc4e6318b394bce1f0f2257fdf8e6c74` |

All four `PORT.json` entries were independently hashed and compared. Storage is byte-identical to the approved candidate. The host's only textual change is the relative package import of storage. The two ported tests only use package-qualified imports. Their registered SHA values also match actual files. This review did not repeat host mechanics adaptation review.

## Driver findings and evidence scope

- **Installed identity:** the driver requires isolated Python, the registered executable/prefix/version and binary hash, installed module paths under site-packages, NumPy version, and identical source/installed module hashes. All registered `files` entries are checked before and after work. Independent tests successfully verified and imported the actual six installed entry modules, rejected a source-path fallback, and detected drift in an additional registered evidence file. Root has agreed that the formal execution freeze will also bind all 165 source and 165 installed package files plus the installed-environment inventory, driver/test/protocol and old references. The environment inventory alone is not the execution-freeze schema.
- **Native acceptance records:** complete `IntegrationResult` states, exact recorded times and `StepLedger` records are saved immediately when a path returns, before any accepted-state decoding/audit. A controlled partial result is preserved and prevents launching the second path. Trial witnesses remain explicitly trial/unknown-prefix evidence. A hard-killed call cannot manufacture its unavailable accepted prefix; only files already written are enumerated.
- **Actual comparison times:** original fine/reference arrays must agree bit-for-bit. The original 99 interior times are passed as breakpoints; the 101 comparison states are selected only by exact accepted-time identity. Missing times are rejected rather than interpolated. The existing 35 differences from reconstructed `k/10` times are explicitly covered by author tests.
- **Absolute conservation:** every accepted prefix accumulates represented ledger exchanges using `Fraction`. Local `Delta E-Q-P` and global `sum(Delta E)-boundary heat` are checked against the unchanged absolute `80 J * 1e-8` bound. Independent opposing local leaks fail even with zero global error and an exactly repaired final state. State/time/ledger cardinality mismatches cannot be silently truncated. Inventory bytes, state identity, zero species terms, absent stretches, and named mechanical-work components are checked.
- **Native local power diagnostic:** initial independent-power diagnostics compared the plate field with reconstructed P. The final revision additionally records `maximum_native_power_reconstruction_difference_w` from actual `Rates.cell_power_w` minus independent per-cell P. A fake `[5,-5] W` corruption is detected despite its zero total. The original plate diagnostic remains; no new threshold or post-hoc stress gate was added.
- **Limits:** native policies retain 60 seconds per path and all pre-registered step sizes/tolerances. The supervisor starts one child only, deducts preflight time from the same 130-second deadline, uses `subprocess.run` timeout/kill-and-reap behavior, never retries, and also refuses success if post-run checks push observed elapsed time to the deadline. Independent fake timing covers this post-worker case. Formal execution must use this supervisor and a root-produced final freeze; the standalone worker is not a replacement for external supervision.
- **Qualification:** fake execution cannot qualify a real native experiment; successful process return alone is insufficient. Scientific success still requires both completed paths, exact comparison points, original thermal/conservation gates, immutable inputs and complete worker artifacts. Stress and independent instantaneous power discrepancies remain descriptive.

All accepted points are decoded and summarized, while full inverse records are retained at the 101 comparison points and worst witnesses. RHS records are summaries plus explicitly identified trial witnesses. This is not a complete field-by-field archive of every RHS or every accepted inverse, and it does not certify unknown continuous-time domain behavior.

The subsequently produced formal `EXECUTION_FREEZE.json` was independently verified at SHA256 `4d1885f5b7b1a034c71a52b3cf0ed69d5ed625b871fef734801f3ecf316a488a`: all 337 registered files and 339 observed identities matched. This last check loaded the driver's read/hash functions only; it constructed no host and ran no integration. The approval binds this final freeze and the file versions listed above.

## Bounded validation

- Author tests: **22 passed in 0.152 seconds**, including fake integration/process boundaries and one actual algebraic point.
- Independent tests: **6 passed in 0.024 seconds**, in `test_independent_driver.py`.
- Both used the actual installed Python with `-B -I`; temporary output was confined to this review directory. There were no native integrations, performance scans, dependency installations or source edits.
- The selected environment does not provide ruff, mypy, pylint or black; source was reviewed and imported/tested directly. Git reports the five port/protocol groups as untracked WIP, with no tracked Python diff; review made no staging/commit changes.
