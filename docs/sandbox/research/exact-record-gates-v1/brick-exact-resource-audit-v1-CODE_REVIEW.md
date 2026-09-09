# Independent resource audit review — repair required

Reviewed source SHA 4cd2c6fc33e7da76a2be455fc05249eaddc423be88e931e878d239d7b6a9b315.

[HIGH] Disjoint ordinary work is combined with max-like lower bounds instead of addition.

Actual pure make record: global ordinary_panels=79, summed refinement ordinary_panels=68, committed ordinary steps=26. Setting global ordinary_panels=68 passes the audit, granting 11 extra remaining panels. Refinement work and committed ordinary work outside refinements are non-overlapping costs, while the chosen refinement is also committed. Count committed ordinary ledgers outside the retained refinement paths and add that count to the refinement sum; do not double-charge chosen path copies. Both individual lower bounds are insufficient.

[HIGH] Materialized terminal panels are not associated with completion telemetry.

Actual pure record attack: terminal_attempts[0] retains its complete terminal_panel, but its terminal_panel_attempts and terminal_panels were each reduced by one, along with global and corresponding refinement values. The audit passes and grants one extra panel. Bind completion counts to the actual saved predictor/terminal panel presence, and require attempts >= those completions. Those proof objects are saved evidence, so this is not an unknowable historical-cost issue.

Both attacks used the existing pure numerical fixture with no EOS, source or repository edits. Original source semantics and limits remain unchanged. Source-bound ordinary discarded-call/wall telemetry limitations are legitimate, but these two undercounts concern work that can be reconstructed from retained evidence. The authoritative-run-store requirement remains necessary; it does not excuse missing available consistency checks.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 2 | warn |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: WARNING — repair both available-evidence cost undercounts before approval.

## Repair snapshot 3a6f3443 — two fixes confirmed, further association gap

The disjoint ordinary multiset accounting and materialized stage/panel checks correctly close the two original attacks. However, an additional actual pure attack still grants one extra panel: delete the first top-level terminal_attempt entry while leaving the complete terminal in the first coarse refinement path, then subtract its predictor/terminal attempt/completion contributions from global and that refinement cost. audit_exact_resources accepts it. The top-level cost-bearing attempt list is not associated with all retained refinement terminal frames.

HIGH: require complete retained refinement terminal attempts to belong to the recorded top-level attempt multiset (accounting for genuine repeated executions, without charging committed copies twice). As a minimal additional lower bound, each refinement's terminal completion/attempt counts cannot be below its materialized frame count. Runnable independent regression is test_review_missing_attempt.py. No EOS/source edits.

Final approval remains pending this retained-evidence association repair. This is not a request for absent RHS history or wall reconstruction: the erased attempt still exists in the saved refinement tree.

# Final repair review — all three HIGH findings closed

APPROVE source c1bfaabb1a3325b26a40cf3fa925e9abaf18aa10278823690cbec5a317285ce0 and tests ef45b0f62086746e98e7b8f980e847c1e139999c9df1749e928990c24b6eee8b.

The final source associates complete packed terminal-attempt values with occurrence counts. The disjoint refinement-frame multiset and committed-frame multiset must each fit the top-level attempted-record multiset independently. This prevents erasing the cost-bearing top-level record while retaining its evidence elsewhere, and does not charge the committed copy as a second execution. It uses full canonical packed values rather than object identity or an unchecked short hash. Earlier disjoint ordinary accounting and materialized predictor/panel/stage checks remain intact.

Independent pure tests: 14 passed in 11.88 s, comprising the 13 permanent cases plus the independently authored deleted-attempt regression (duplicating that repaired attack intentionally). All three actual undercount attacks are now rejected. Earlier REDs and preliminary dispositions remain recorded above; this final snapshot supersedes them.

The original charged-panel formula, rejection limit and wall allowance semantics remain unchanged. Remaining wall is the nonnegative difference from the full saved elapsed telemetry; overrun telemetry is preserved, not clipped. Original policies and canonical record bytes are revalidated, and returned counters/maxima are immutable. It remains a recorded-consistency audit requiring authoritative parent bytes; it does not prove omitted discarded ordinary-call history or historical wall authenticity and does not grant continuation authority. Full numerical acceptance and service parent-lineage safeguards remain separate prerequisites.

No EOS, installation or repository/source edits occurred in this review. No further blocking findings for this bounded contract.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — recorded resource consistency and original remaining allowance only.
