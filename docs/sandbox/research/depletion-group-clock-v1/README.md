# Explicit affine multi-root implementation

New source: `src/sludge_sandbox/depletion_group_clock.py`; tests:
`tests/sandbox/test_depletion_group_clock.py`.

The exact polynomial is N(h)=N0+r0*h+a*h²/2. This is an explicitly
manufactured model. A grazing zero also ends strict positivity; its root does
not authorize a dry-mode switch. Interval groups include all first roots and
use the union. Strict ordering edges are reported separately even when the
numerical time gate clusters nearby roots. No liquid correction is performed.

`PLAN.md` records the validation contract. `CODE_REVIEW.md` approves the
implementation. `LOCALIZATION_REVIEW.md` identifies missing real wet RHS
remainder evidence. The first test run failed because its independent test
used the wrong sign for an equivalent quadratic root equation; that log is
retained. No production change or relaxed tolerance made this pass.

Actual source command (exit 0):
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests/sandbox /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest tests/sandbox/test_depletion_group_clock.py tests/sandbox/test_affine_depletion_clock.py tests/sandbox/test_affine_depletion_guards.py tests/sandbox/test_affine_depletion_integration.py tests/sandbox/test_depletion_multicell.py -q
```
80 passed in 30.10s. After frozen offline non-editable uv installation,
from /private/tmp without PYTHONPATH, the new test file passed 16 tests in
0.03s. All 66 installed sandbox modules matched source. Output files here
record these executions; no native physical experiment was run this increment.

Next implementation: explicit affine joint-event state/correction and shared
ledger tests, followed by an explicit numerical closure for real wet group
localization. This primitive alone neither authorizes joint switching nor
resolves the original spatial failure. Full Goal acceptance remains open.
