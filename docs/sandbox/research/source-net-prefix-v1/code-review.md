# Affine quadrature/source prefix independent review

Read exact_terminal_panel extraction diff and current source_net_prefix implementation/tests. Helper exact affine formula/state update preserve legacy ordering, rounded underflow/overflow refusal and original state-only tolerance gate. New helper exposes exact integrals and signed projection residual separately. Complete13-record legacy fixture and helper tests passed in reviewer invocation; see HELPER_TESTS.log. No EOS or repository edits.

Source prefix revalidates source panel, exact interval, all-positive starting fluid inventories and whole-prefix minima; zero-initial cannot be silently omitted. Integral projections, represented state projections and full state-minus-exact-polynomial residuals are separately recorded and gated. Phase signs share one projection, total face U authoritative, physical liquid enthalpy is not counted as decomposition roundoff. Raw numerical boundary status does not authorize wet-state acceptance/writeback. Rebuilt checks validate arrays and derived metadata against source evidence.

[HIGH] Cumulative audit drops integral projection residuals across prefixes.
Actual pure manufactured probe: h=(2**54+1)/2**54, constant liquid face rate2**54, large positive initial inventory. Each prefix integral loses1mol while represented state update is exact; local full residual1 is within1.5mol tolerance. Two contiguous prefixes have cumulative full exact residual2>1.5, but audit_source_prefixes accepts and reports residual0 because it sums only rounded ledger. probe_cumulative.py/log and failing CUMULATIVE_RED.log retained.
Fix requested: preserve represented-ledger residuals and additionally accumulate exact quadrature net exchanges/full residuals under the same cumulative budgets. Do not claim cumulative full arithmetic budget from represented state-only bound. Parent/provider notified; final review pending repair.

## Final correction/guard review

Cumulative audit now preserves represented exchanges/residuals and independently sums exact quadrature net exchanges, gating both represented and full exact residual after every prefix. The original true two-prefix RED now passes expected rejection at cumulative_full_inventory_budget. Neither signed net gate claims an absolute accumulated error-cost bound. Original policy-field tuple is recorded and revalidated before rebuilding, preventing tolerance changes from silently relaxing a retained prefix. Known face classes are enforced before diagnostics.

Shared source-panel validation now checks exact int/None face identity/adjacency and exact finite float64 ndarray state/rate fields before shape/mapping on both samples. These guards strengthen record assumptions without altering valid coefficient arithmetic; existing derived reconstruction remains.

Actual final reviewer run56passed0.37s: original cumulative reproducer,27sourceprefix tests,28sharedpanel tests. Earlier helper/legacy run12passed0.09s retained. No broad source suite or EOS replay performed. Provider final source8bcaef.../testcbd2e4... hashes checked against manifest; all eight scoped files parsed/bound in FINAL_FREEZE.json. No unresolved critical/high functional defect identified after corrections; scoped approval applies to these bytes. Boundary results remain numerical and do not authorize physical state/writeback/event acceptance.
