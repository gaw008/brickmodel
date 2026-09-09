# Exact affine root and writeback candidate

Frozen implementation SHA256: 8448d3196084116b4b80c5348c48692665017490f969b2b94f505c7bb8601548
Frozen tests SHA256: 67ce2da49a017879cf1860a6be35c84a351cebb5b3facaf5e73820d840687a85

Only temporary files were written. No repository changes, EOS, installation, or commits. The first test collection syntax error is preserved in tests01.log. tests02 passed eleven cases; tests03 passed all fourteen in 0.07s. Exact command: `PYTHONPATH=src /private/tmp/brick-water-backend-probe/venv/bin/python -m pytest /private/tmp/brick-exact-affine-depletion-v1/test_exact_affine_depletion.py -q`.

## Types and contracts

ExactAffineSamples binds explicit ExactEventTime start/midpoint/domain upper, original represented initial liquid, three separately signed left-face/negative-right-face/source rates at each sample, and separate signed evaporation samples. It validates positive initial inventory, complete finite triples, strictly decreasing total inventory across the WHOLE domain, a bracketed first root, and explicit immutable unique source labels. Source labels identify supplied samples only; they are not a proof of an actual provider or physical source. The full host/source identity bridge remains required.

ExactAffineEvidence records a lower rational endpoint and an upper enclosure in adjacent dyadic bins of the declared domain at a bounded refinement level. Rationals have no nearest member below an irrational root; this is an explicitly stated finite-grid lower enclosure, not an exact irrational root or global nearest rational. The constructor checks adjacency, domain, monotonicity, nonnegative lower and nonpositive upper inventory, and the original time/absolute/local-ULP/fraction correction budgets. The locator refines until those SAME gates pass, with a fixed maximum 256 levels. It does not replace the original time gate with a smaller hidden policy.

Every signed component is integrated exactly then rounded to binary64 once. Gross evaporation integrates the positive part of the signed affine evaporation sample and rounds down. A complete signed-term mismatch cannot be bypassed even if the raw liquid is zero. The evidence is revalidated at writeback; callers cannot supply a different policy or larger evaporation denominator.

exact_depletion_writeback retains the existing state's energy, mechanical state, and unrelated inventory. It uses the ORIGINAL DepletionRoundoffPolicy and DepletionRoundoffTotals, sharing existing _check_budgets and _half_neighbor_spacing helpers; the boundary-specific orchestration reproduces the unchanged physical phase/storage checks in a separate function. Its result record is a distinct ExactDepletionWritebackRecord. A zero raw liquid returns the input unchanged and correction None after evidence validation. Failed cumulative or storage checks never mutate the old state/totals. This is not a group-mode transition and does not authorize use of old event codecs.

## Actual saved fixture and tests

saved-cell2.json contains the selected actual samples/old root evidence and original policy, with the SHA of the full native failure record. The original binary64 clock/writeback still raises correction_exceeds_evaporation_fraction in the test. The new affine enclosure needs 26 levels; width 1.2594605684618096e-17 s, represented residual/gross ratio 9.226387713494241e-9, under the unchanged 1e-8 fraction gate. No earlier-panel or other-cell evaporation is borrowed. The actual coupled wet RHS is not reevaluated.

Tests also cover independently computed multiple nonzero signed components, both directions of evaporation zero crossing, zero correction, mismatched terms despite unchanged net, cumulative refusal, malformed inputs/evidence, and exact duration/term invariance for origins zero, saved time, and 10^12. The compact raw state used for writeback tests is an accounting fixture with sentinel unrelated N/E/stretch, not a reconstructed whole physical terminal panel.

## Required ordered packet bridge

1. Sample the actual FULL Rates at the exact current start and midpoint on the wet path, with the actual source/model/mode binding and time-aware provider contract. Preserve initial/midpoint full states/observations, not just this helper's selected-cell rates. Stop with original failure evidence if a provider accepts only display floats.
2. Reconstruct every species/cell inventory polynomial from those SAME component samples and exact interval. On the entire candidate interval, independently check endpoints and the interior vertex when convex. All inventories must stay nonnegative, and all positive competing wet-liquid inventories must remain strictly positive until their own transition. Do not substitute selected-cell monotonicity for this full-panel check.
3. Construct/refine enclosures for all still-wet candidate cells, including possible earlier nonmembers. Only choose a cell when its upper bound is strictly below every competitor's lower bound; exact coincidence/unresolved ordering remains unsupported. The original time gate is an upper error bound, not a minimum separation requirement. A pure rational clock bracket does not certify the actual nonlinear RHS root.
4. Integrate all N/E/power components/stretch from the shared affine sample with the SAME chosen exact endpoint. Construct an ExactStepLedger and complete raw state; pass its matching selected signed terms and local positive evaporation to exact_depletion_writeback. Re-audit full original cumulative budgets before global commit. Do not relabel this state with its display time.
5. Apply the actual mode switch only on the speculative path, then evaluate the changed mixed RHS using the exact clock. Continue to a shared exact common endpoint, preserving all event frames/corrections/semantic times. Keep two successive passes and the independent approach with original N/E/T/P/stretch/time gates and full resource accounting. Commit the packet exactly once only after all original criteria pass.
6. Add explicit new typed packet/event record schemas and strict restore/audit support before service resume. Current old schemas must refuse these new clock/record types. Runtime/source binding and the shared-constant pressure comparison contract must be carried without changes to physical meaning.

The candidate completes the selected-cell exact affine accounting component, not the above full bridge. It does not close the failed native run, material admission, spatial convergence, or a complete firing model.

Copy exact_affine_depletion.py, the permanent test, and saved-cell2.json fixture only after review. conftest.py is temporary loading infrastructure. make.py/writeback-part.txt preserve initial generation; the frozen module includes final validation refinements beyond that initial generated fragment. Independent numerical review has been requested.
