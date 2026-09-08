# Next numerical priority: program-knot residual panels

Read-only diagnosis from retained affine-terminal XML/test bytes and current integration/depletion scheduling. No model/EOS imports, no tests or source edits. Only standard-library arithmetic was used to examine represented times. The current four-cell native run was not touched.

## Retained actual failure and smallest cause

/private/tmp/brick-affine-terminal-v1/second-integration-tests.py changes both initial_step_s and maximum_step_s to .005, retains the manufactured adapter's knots (.05,.15), and runs the same prior physical/oracle cases. second-integration-tests.xml preserves four unresolvable_stage_time failures, including the failure-injection test that never even reaches affine_terminal. The original .01 case with tighter ordinary accuracy passes; that does not fix or erase the .005 failure.

The important scheduling boundary is outside the standalone ordinary RK integrator. depletion_integration.py chooses an ordinary finish approximately as min(tb, t+maximum_step, t+safe_fraction*tau) and calls normal(), which creates a new ordinary integrate() invocation for that one segment. Each invocation therefore resets its exact Fraction clock to the rounded segment start. The standalone integration.py exact clock cannot prevent drift accumulated by the outer caller across multiple independently rounded segment endpoints.

For an inactive inventory limiter, standard binary64 arithmetic gives:

- ninth start .04, finish .045;
- tenth start .045, finish .049999999999999996;
- known next program knot is .05;
- difference is 6.938893903907228e-18 s, exactly one ULP at .05.

The next outer segment is then [.049999999999999996,.05]. These are adjacent binary64 values. There is no representable strictly interior midpoint: the computed midpoint rounds to .05. The stage guard `at < midpoint < next_time` correctly refuses it. This arithmetic is a source-backed explanation of the retained failure trigger, not a newly run model reproduction. The saved XML does not itself include every internal variable; the minimal test below should first confirm this exact trigger on the unchanged source.

## First implementation target

Fix the outer segment endpoint selection in depletion_integration.py, not the invariant that an RK step needs a representable midpoint. While still at the preceding resolvable state (.045), coalesce a proposed endpoint that is one bounded rounding unit below a KNOWN program boundary onto that boundary, then integrate the complete [.045,.05] panel with its actual endpoint-derived weights. Do this before executing/committing the penultimate panel, so no inventory/energy evolution is skipped.

Use the same deliberately bounded spirit as integration.py's existing endpoint guard: target gap must be positive and no larger than both one ULP of the known boundary and a small ULP allowance of the intended panel duration. Do not use an absolute epsilon such as1e-12, a blanket relative time tolerance or event acceptance tolerances. Do not coalesce arbitrary safe-inventory/event-limited endpoints onto distant boundaries. Verify the boundary is the immediate permitted target and the rounding adjustment cannot cross a physical/program/event limit. Preserve the actual rounded duration in every state update and ledger, and record the ordinary panel ending exactly at the knot once.

The source's existing local guard uses min(ulp(target),32*ulp(min(h,target-at))); a narrowly scoped reusable endpoint-choice helper may make caller/core semantics consistent, but it must not become a broad integrator redesign. If no defensible bounded coalescing is possible, retain the explicit resolution failure. Never advance only the timestamp, silently skip the tiny interval, fabricate a zero-duration ledger, allow identical midpoint/end states, or relax amount/energy source budgets.

The same outer scheduling idiom appears in ordinary approach/dry continuation. Audit those call sites for the identical represented-endpoint issue, but implement only proven/common cases with independent regression coverage. A future boundary can be a physical discontinuity; no stage may evaluate across it merely to avoid a residual panel.

## Minimal independent no-EOS regression

First create a synthetic ManufacturedDepletionAdapter with a comfortably positive liquid inventory, a constant small liquid-to-vapor source and constant power. Give it one interior program knot .05, start0/end.06, initial/max ordinary step .005, no nested approach and no near depletion (choose inventory/sink so tau is much longer than the entire interval). Constant sources have analytic inventory and energy integrals; there is no affine terminal, EOS, nonlinear reaction or spatial transport to confound the test.

On original source this should expose the same one-ULP residual segment. Save original failure status, all accepted times/steps and exact hex endpoints. If it does not reproduce, do not claim this hypothesis proved; use the retained b=0 fixture directly and inspect its saved prefix before narrowing further.

After the fix require completed status, exact .05 and .06 endpoints in strictly increasing times, no duplicate/zero-duration panels, no ledger crossing .05, and exact source/energy integrated to the declared end within original representation allowances. A fresh standalone integrate() test with the same constant source and breakpoints=(.05,) is a useful control: its persistent Fraction clock may already avoid this defect and should not be broken by the caller fix.

Add bounded neighbors: a dyadic .00390625 step control; a nearby genuinely representable small final interval that must still be integrated; a non-coalescible sub-minimum physical interval that must remain a failure; and a piecewise rate schedule at the knot verifying no before/after segment integrates the wrong branch. Match the documented one-sided endpoint convention rather than assuming smoothness through a discontinuity. Verify cancellation/resource status and all accepted prefix ledgers survive. Finally rerun the exact retained .005 affine/depletion fixtures at their original unchanged acceptance gates; this confirms that the practical blocker, not only a toy clock case, is resolved.

No native EOS is needed to establish or test this scheduler defect. Source review and existing ordinary/depletion regressions are required before another installed native run; the full wet/source tests remain a later controlled regression stage.

## Why this has higher priority than more tiny mesh pilots

Programmed firing/cooling requires stepping through many specified ramp/hold/atmosphere transitions. Failing at an ordinary representable program knot blocks long schedules regardless of how accurate the local EOS, terminal event locator or spatial flux assembly is. The present extremely short dyadic spatial pilots deliberately avoid those transitions, so adding more such cells cannot resolve this integration reliability gap.

A successful two-to-four manufactured spatial comparison can provide useful local resolution evidence, but its discontinuous initial temperature jump and tiny elapsed time do not demonstrate whole-firing convergence. Complete its current evidence archive, then address this small deterministic knot regression before continuing to broaden schedule length/complexity. This does not redefine the Goal: raw-material provenance, source-complete constitutive behavior, physical free sintering and full firing/cooling remain necessary separate deliverables. The proposed fix only removes a reproducible numerical obstacle on that path.
