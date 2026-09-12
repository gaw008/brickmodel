# Independent saved-prefix review: native01

**Saved-prefix evidence is internally consistent; the original experiment remains failed.** This review read existing JSON and used only standard-library exact rational arithmetic. It constructed no host, made no model/evaluator calls, and ran no integration or replacement trajectory.

The original terminal state is `numerical_failure / unresolvable_stage_time`, with 61 accepted states, 60 returned StepLedgers, 421 RHS calls, no rejected trials, and no fine-path start. The supervisor records exit 1, child reaped, no timeout, elapsed 0.7105093339923769 seconds, and identical 339-entry before/after input identities. Its `passed=false` remains unchanged.

The last accepted time is 0.3 seconds (`0x1.3333333333333p-2`); the next original comparison time is 0.30000000000000004 seconds (`0x1.3333333333334p-2`). Only **three** accepted states match the frozen reference times exactly: accepted indices 0, 20, 40 at 0, 0.1, 0.2 seconds. This report records the adjacent represented times; it does not implement or validate a clock repair.

Every saved accepted prefix was independently reconstructed from original E and represented face-energy/work ledger entries using `Fraction`. The reconstruction agrees exactly with every stored audit row and maximum:

| Quantity | Maximum absolute residual |
| --- | --- |
| Per-cell Delta E minus accumulated face heat and local work | 3.742027439402418e-14 J |
| Global Delta E minus accumulated boundary heat | 4.441585987891017e-14 J |
| Accumulated total constraint work | 1.824135082748889e-18 J |

The first two are below the unchanged absolute 8e-7 J conservation threshold on this returned prefix. Inventory values, float64 bytes, energy identities, absent stretches, zero species exchanges, actual ledger endpoints, and mechanical-constraint component equality were also checked across all saved states/steps. This is not completion of the registered 0–10 second gates.

The three comparison inverses and four worst-witness inverses were independently recalculated at their actual returned binary64 T values using the exact binary-input energy map. All seven retained records satisfy the original energy/temperature policies and the public residual-norm versus radius-times-capacity certificate. Initialization forward rounding was separately checked. The initial returned values 304.0000000000011 K satisfy the retained 1.6286322282341645e-12 K vector error certificate relative to the exact uniform root for target E=(40,40) J.

The recorded maximum native per-cell power reconstruction discrepancy is 4.0657581468206416e-19 W over the RHS summary. The full per-RHS fields are not archived, so that online maximum cannot be independently replayed from the saved artifact set. Accepted-state summaries report 61 successful decodes; only the retained complete inverse records were independently recalculated here. The original coarse-rhs-trials file is empty because no 512-call witness was reached.

The maximum temperature difference among the **three available comparison points** is 1.7838374333223328e-8 K against either old temperature path. Both complete reference-comparison gates and coarse/fine convergence remain false/incomplete. No real-material, chemical-mass or full-cycle qualification follows.

Reproducible arithmetic is in `audit_saved_prefix.py`; results and seven original-file before/after SHA256 pairs are in `SAVED_PREFIX_AUDIT.json`. All seven reviewed artifacts remained byte-identical. No failure artifact was rewritten.
