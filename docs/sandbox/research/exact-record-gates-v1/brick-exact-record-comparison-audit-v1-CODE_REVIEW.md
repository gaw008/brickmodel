# Independent comparison audit review — pending repair

[HIGH] Untrusted coarse status bypasses original approach-policy binding

File: exact_record_comparison_audit.py, refinement grouping and final committed group selection.

Actual pure attack changes the initial coarse status to an arbitrary string and doubles every approach cap; audit still succeeds under the unchanged external policy. The original coarse checks execute only if the altered status equals coarse_reference, and the final group match does not require that original anchor. See REVIEW_ATTACK.md for exact source/record hashes and actual result.

Fix: require each committed comparison group to begin with a genuine level-zero terminal coarse_reference with no comparison payload and original controls; validate its subsequent role/status/level chain before treating relative half-controls as evidence of original-policy compliance. Preserve legitimate retained failure diagnostics separately.

The remaining six-gate arithmetic follows the prior reviewed saved-data auditor; full actual pressure bindings are recomputed from mode-specific original operators and pure pressure certificates re-audited. The paired helper tests exercise real pure certificates; complete actual-host paired integration is still a separate native saved-record check. Original-prefix/root/resource omissions remain explicit. No EOS was used in this review.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 1 | warn |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: WARNING — resolve the HIGH original-policy bypass before approval.

# Final coarse-anchor repair — supersedes preliminary disposition

APPROVE source 1cef63c34c9cf77c51a62078df0b696dae2c33096140b079f8b0d8c79b988368 and test f4064bb5961537480ba2721bf4fc53f60fab9638f497a63778d14341c52d2959.

The complete repair diff now independently requires each committed matched group to start with an actual level-zero terminal coarse_reference, no comparison payload, retained path and original approach/safe/window controls. All subsequent terminal stages must have legal comparison status, nonempty comparisons, consecutive levels within the original refinement limit, and the final independent stage must match its preceding level. Existing half-controls, distinct pre-first-event grid and six-gate recomputation remain unchanged. The reproduced invented-label/doubled-cap bypass is closed; prior attack and RED evidence remain retained.

Independent final pure tests: 14 passed in 12.46 s, including the original attack and malformed coarse comparison, intermediate role and initial level. Source/pressure binding uses actual mode-specific reconstructed operators and exact complete binding comparison. Paired certificates are re-audited with all cell states and reported original error vectors associated; endpoint counts remain separate from host evaluations. Both event and common-state six-gate maxima and committed frame links retain original thresholds. Full pipeline fixtures use instrumented providers; the paired helper test independently uses actual pure certificate arithmetic. A real saved native-record plus actual operator check remains separate evidence.

No additional blockers found for the declared partial comparison audit. It does not grant original-prefix/root/resource or resume authority, and does not re-evaluate EOS or certify omitted inverse objects. No EOS, installation or repository edits were performed.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — earlier HIGH resolved; original comparison gates only.
