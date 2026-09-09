# Actual ordered packet writeback failure arithmetic

The saved-data audit passes; the simulation remains FAILED. The original fraction gate correctly rejects the second speculative terminal panel. This evidence does not establish a committed packet or spatial convergence.

Command: `python3 /private/tmp/brick-ordered-packet-failure-native-audit-v1/audit.py /private/tmp/brick-four-cell-ordered-failure-evidence-v1/attempt01` (exit 0). Only Python standard-library JSON/Fraction arithmetic; no solver imports, tests, EOS or production edits. Input SHA256 bindings and exact rational results are in audit-result.json. Runtime-before and runtime-after are exactly equal.

Actual first speculative event is cell 3. Its certified numerical affine root interval lies strictly before cell 2 by at least 8.452094579780578e-10 s. The next, freshly evaluated mixed-mode terminal panel selects cell 2; its represented duration is 8.452095690003603e-10 s. Both saved root-order records pass polynomial endpoint sign, decreasing-root and strict first-root checks. This is numerical surrogate ordering, not a true-RHS event certificate.

For the failed cell 2 panel:

| Quantity | Saved-data recomputation |
|---|---:|
| Raw liquid correction delta | 5.673486681192076e-20 mol |
| Exact positive evaporation integral | 1.5641070214850038e-12 mol |
| Greatest downward represented integral | 1.5641070214850036e-12 mol |
| Original 1e-8 fraction allowance | 1.5641070214850035e-20 mol |
| delta / evaporation | 3.6273008197389976e-8 |
| Factor above allowance | 3.6273008197389975 |
| Affine polynomial remainder at downward clock | 5.673486686333683e-20 mol |
| Raw delta minus polynomial remainder | -5.141607489530308e-29 mol |

Thus nearly all actual residual is the nearest-downward absolute-clock root remainder, rather than integrated-component rounding. The relative correction budget shrinks with the very short interval after cell 3. This is a measured mechanism for this failure, not a general claim that every near event must fail. Neither relaxing the gate nor zeroing both initial ties is justified by this audit.

The audit independently reconstructs signed start/midpoint liquid rates and once-rounded affine terms, the full raw N/E/mechanical update, the evaporation positive-part integral and downward rounding, nearest-downward root enclosure and original clock tolerance, and both failed/previous surrogate root-order records. It requires exactly one failed diagnostic, nonempty accepted prefix and preceding speculative frame, zero committed events/packets/corrections, and matching original roundoff policy. It does not duplicate the separate original-prefix ledger audit or purport to re-evaluate saved thermodynamic observations.

All 13 accepted steps remain distinct from the uncommitted cell 3 event and rejected cell 2 attempt. Previous frame event metadata is not accepted refinement evidence. No event/common-state comparison passed before this rejection. The next numerical design must preserve the fraction limit while addressing represented event-time accounting; this report does not implement or approve such a change.

Independent code review prompted additional guards: exact three signed terms; full mechanical shape; unique and complete active-cell root rows; root coefficients bound to actual saved start/mid observations; failed panel initial inventories bound to its saved start state; root brackets within the declared panel; clock tolerance and roundoff policy bound through actual policy to original case. The saved-data audit passes again with these guards.

Important evidence limit: the previous cell 3 frame does not save its full start state. Its root-rate coefficients and complete active-cell set are bound to observations/modes, but nonselected initial inventories in that prior root proof can only be checked as stored polynomial inputs. Therefore its ordering is a consistency audit of the saved numerical proof, not a complete independent reconstruction of the prior speculative trajectory. The failed cell 2 panel does contain the complete start state and supports the direct residual diagnosis above.
