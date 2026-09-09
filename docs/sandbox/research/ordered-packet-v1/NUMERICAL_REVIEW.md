# Ordered affine packet core: final numerical review

Reviewed source SHA3866f15b11f0e78c4e77591ffb8fe156bafefe05a379165ff78e635fe52c3223 (verified from actual file), and current test_depletion_ordered_packet.py. Read-only; no tests/native EOS executed by reviewer. Author reports14new+35legacy tests passed8.33s.

Verdict: **approve the bounded core numerical implementation**, with explicit pending service/record and actual-native validation. No remaining blocker found in the reviewed scope. This is empirical numerical affine-surrogate ordering, not a validated true-ODE root certificate.

## Previous blockers resolved

- normal now catches _PacketReplan through the existing integration error boundary (557–573), retaining the actual integrate result as accepted_prefix and charging the interrupted panel. continue_packet (797–823) passes a stage checker when wet cells remain, appends only accepted substeps from that prefix, and returns to fresh observation/terminal localization. No mode switch occurs at an internal RK stage. Source/domain/cancellation failures do not become ordinary successful panels.
- Forced replan without a currently localizable before-common-time root fails explicitly (801–802). This prevents identical no-progress retries. Terminal clocks still require a representable positive midpoint and endpoint and preserve original domain/positivity checks.
- Acceptance now annotates every frame (1203–1210) with corresponding first-coarse and previous event times plus actual common time. The difference fields carry the accepted conservative packet-wide maxima, not falsely zero member diagnostics. Detailed per-frame comparison records remain available; consumers must label these fields as packet maxima rather than member-specific measured differences.

## Numerical ordering and comparison

The ordered affine branch640–674 forms all wet numerical polynomials from common start/midpoint observations. It selects an earliest isolated root only when its upper bound is strictly below the next lower bound. The original time tolerance is not misused as minimum separation. Polynomial coefficients/root-rounding remain based on actual represented sample values. Exact/overlapping intervals remain unsupported rather than arbitrarily index-ordered.

After each accepted speculative mode switch, subsequent localization uses the actual new operator/RHS. Path frames retain all intermediate corrected states and pressure snapshots. Comparison matches the entire cell sequence and final modes; it invokes original single-comparison checks on each frame plus the shared common endpoint, and aggregates maxima. Both consecutive refinement passes and the independently halved approach controls remain required. Root source/spine binding is rechecked before final commit. Unsupported ordering changes cause failure rather than an unverified permutation.

## Accounting/transaction review

Commit creates a unique terminal-panel identity map and rejects duplicate association. Before each step's cumulative N check, it selects the corresponding frame event; therefore each liquid/vapor correction is applied once at its own panel. Every step retains original-initial E/N/component/mechanical represented/exact/absolute-roundoff checks. Global times/states/modes/events are extended only after complete speculative path validation. All frame events/corrections are appended once, preserving exactzero correction=None.

Repeated stage previews consume evaluations; interrupted packet panels are explicitly charged. Pure callback preview tests are correctly labelled control-flow fault injection, not independent physical trajectories. More realistic accelerating-RHS and actual4cell runs remain useful validation but are not concealed by these tests.

## Boundaries before broader claims

Ordered continuation is explicitly rejected; packet service serialization/auditor support must not be inferred from core success. Existing legacy event auditor assumes one event/common record structure and needs a separately reviewed packet schema. The source remains an opt-in method, with default single-event behavior separately regression-tested. No tolerance, physical coefficients, source envelope or shared-error family is loosened.

A bounded actual4cell short-event probe and independent saved-prefix audit are the next relevant evidence. Failure remains a valid result; this review does not claim actual4/8 near-events, longer-time spatial convergence, raw-sludge physics or true event-time uncertainty have been solved.
