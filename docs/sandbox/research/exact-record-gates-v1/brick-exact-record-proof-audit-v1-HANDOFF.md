# Committed exact terminal proof audit

Frozen source ff991e946c72953c1e8a844cfc7c42165cd52b94ddeded9bb43ef2d49fc2ef7b.
Portable test 8af12800e157cdb28686bdbd33ab9048239dd8f1a81a4813622fea946d668373.
Actual tests02: 10 passed in 11.06s. No EOS, installation or repository edits.

API `audit_committed_terminal_proofs(raw, *, original_operator, original_initial, start, end, integration_policy, event_policy, case_sha256, runtime_identity) -> TerminalProofReport`.

The function consumes the freshly returned validate_binding record and matches all external original inputs/policies. It visits every committed terminal, not only the last/selected record. Its fixed numeric reconstruction whitelist never builds providers or live inverse objects. It binds actual first/midpoint/endpoint roles, states, modes, phase coefficients/source declarations and original energy identity. Actual CurrentSolidStorage._prepare recomputes per-cell geometry/pore volume and state/domain/source guards from each observation's full normal/tangent and solid inventory without EOS.

For every terminal it reconstructs the exact tau hint, predictor and domain; recomputes all candidate roots and no-root exclusions through verify_exact_root_order; reconstructs every N/E/component/mechanical predictor and terminal field through build_exact_affine_panel; and replays exact_depletion_writeback with original cumulative correction totals and all original local/absolute/fraction/storage/element/mass budgets. Exact comparison of complete value records includes derived quadrature fields. Endpoint state/mode and final cumulative totals must match. Geometry results from actual point preparation are retained in immutable per-terminal report rows.

This gate concerns the numerical affine surrogate and data-source association. It does not evaluate the true EOS/RHS again or reconstruct omitted thermal inverse trees. Reported T/P samples are checked against actual source domains, not certified anew as solutions of the inverse problem. It does not replace original-prefix conservation, six-gate empirical refinement comparisons, cumulative resource auditing or continuation admission. Those missing gates are explicit in the returned report. A result with zero committed terminals is a vacuous terminal audit, not proof of any completed event.

Tests: real exact integration/root/panel/writeback numerical chain with intentionally instrumented host samples; tampering of candidate coefficients, nonselected exclusion, predictor energy, midpoint Rates, source label, cumulative input totals and original policy; separate actual CurrentSolidStorage dry geometry/domain check using the existing forbidden-water fixture; separate unpatched observation coefficient/source/state contract checks. The end-to-end numerical fixtures stub host geometry/observation binding because their existing typed host shells are incomplete; they do not claim a full real-host proof. The real geometry and source-association helpers are tested independently. Parent owns any actual saved-native-record plus real rebuilt-operator check after review.

Apply only exact_terminal_proof_audit.py and test_exact_terminal_proof_audit.py after review. The conftest.py is a temporary relative-path candidate loader and must not be applied. Tests use formal package imports and existing test helpers without absolute temporary paths.
