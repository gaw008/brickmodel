# Prepared source inverse-pressure runner review

APPROVE for `docs/sandbox/research/source-inverse-pressure-v1/run_saved.py`, SHA-256 `ec89719e1cdee5709d0baa571601b7951577b3be39d4dc5655e0e44c623be094`, and the stated one-shot execution scope. This review did not execute the runner or any EOS.

The runner verifies the frozen actual source trial, its audit, the existing passive decoder, original storage constructor and prior independent Fraction endpoint artifact before using them. The original constructor path and `HEOSCandidate.__init__` were read. Two completed HEOS backend constructors each execute one direct DmassT reference-anchor native update, followed by ideal-enthalpy/entropy anchor checks. The recorded anchor count is justified by this fixed successful constructor code path; it is not a measurement of every possible internal native operation. The run must not be described as containing no EOS work.

During construction and saved-record processing, eleven public source, storage, real-fluid state/response, phase-equilibrium and saturation entry points raise on any attempted new endpoint calculation. The constructor's direct reference-anchor update remains deliberately permitted and separately counted. The script neither evolves an integrator nor calls a temperature inverse. It reconstructs one actual fixed storage whose identity must match each of the six saved endpoint records; normal source, caloric, closure residual/resolution and original error-bound checks are applied before conditional propagation.

Both global and bootstrapped slopes/radii and all three pair bounds are compared exactly with the pinned independent artifact. Positive available-volume uncertainty is required in all six actual records. No event tolerance is invented: the saved case has no event policy, the conditional gate remains null, and source/event/material certification remains false.

The preregistered limits are 20 s soft and 30 s outer. The outer signal is active during construction and processing; failure saves the exception, completed work and constructor/forbidden-call counts, then propagates. The prior signal handler is restored and timer disabled in `finally`. The soft limit is a completion-time check, not an interrupt between every pure arithmetic operation. This distinction is consistent with the declared soft/outer resource arrangement.

No confirmed unresolved defect in these runner bytes. Source/install checks and the other independent reviews remain separate prerequisites for the actual one-shot execution.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — prepared six-record conditional accounting with two disclosed native reference-anchor constructions.
