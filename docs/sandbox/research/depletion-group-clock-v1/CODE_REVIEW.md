# Affine multi-root primitive review

APPROVE. Read full new source, tests, and registered PLAN.md. Git tracked/staged diffs are empty; these scoped files are new/untracked. No edits to source/tests, no EOS, no test rerun.

Source SHA256: 20b30a55c08a3c4155b4af9b2c03b858f35f7f61863406d038fcdfc0108d353b
Tests SHA256: 3ad269fb3028df4440382b352128739ae831c2a66244302eb1edde7cfee72bc0
Retained test output:16 passed in0.04s. Tests use explicit polynomial models; no real wet admission is claimed.

First-root reasoning: initial inventories are strictly positive. For upward convex inventories with initially negative slope, isolation stops at the vertex or declared endpoint, so sign bisection cannot return the second crossing. Convex initially nonnegative-slope inventories cannot deplete. Linear or concave inventories starting positive have at most one positive crossing; concave initial growth therefore does not invalidate the sign bracket. Endpoint-zero and tangent-touch cases are handled exactly. Exact midpoint termination and exhausted bisection budgets are explicit.

Positive-panel minima include endpoints and the interior minimum for positive acceleration. group_roots recomputes the complete set of cells whose domain minima reach zero, rejects missing/duplicate roots, verifies first-branch endpoints, and requires exact polynomial zero for point intervals or strict lower positivity plus nonpositive upper endpoint otherwise. Thus exact_common_root requires every validated member interval collapse to the same exact rational root; neither equal instantaneous ratios nor overlapping uncertain intervals produce that status. Connected interval clusters preserve the union, including wide transitive chains. Strict order edges are emitted only for strictly separated enclosures.

Input constructors require exact Fraction coefficients and immutable complete cell inventory tuples with explicit nonnegative unique indices. Bool/int confusion is rejected where IDs or budgets must be integers. Outward absolute conversion encloses represented rational endpoints using adjacent binary64 values and rejects unrepresentable finite bounds. It is a conversion helper, not an independent root-membership auditor: callers needing a root certificate must retain group_roots validation; its docstring appropriately makes only a time-enclosure claim. Large-origin rounding is not used to infer common exact roots.

Tests cover unequal roots despite equal tangents, common roots despite different tangents, earlier omitted cells, union chains, negative interiors, double-root touch, growth-before-depletion, irrational isolation width, precision exhaustion, invalid types and false exact-root claims. The corrected irrational test uses independent quadratic signs plus the original width rather than an unrelated decimal window; this directly proves enclosure without weakening production resolution. No concrete blocking issue found.

This remains the explicitly manufactured zero-remainder affine-rate primitive. Native callback admission, clustered corrections/mode switching, records/resume and spatial validation remain outside this increment.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — bounded primitive and tests only.
