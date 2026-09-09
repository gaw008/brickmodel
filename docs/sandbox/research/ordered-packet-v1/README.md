# Ordered event packet core: implementation and actual failed probe

Baseline `cd89a46`. This change adds the explicit numerical policy
`ordered_affine_packet_v1`, preserving default single-event behavior. See
[the implementation contract](../../ORDERED_EVENT_PACKETS.md), `PLAN.md`,
`CODE_REVIEW.md`, `NUMERICAL_REVIEW.md` and `BOUNDARY_REVIEW.md`.

## Verified implementation scope

The core compares every speculative event's complete state and a common
endpoint, using two consecutive refinements and an independent finer approach.
Strictly separated affine numerical root intervals determine ordering; this is
not a rigorous enclosure of the nonlinear physical trajectory. Each mode switch
uses the resulting mixed-mode operator. A packet commits only after complete
prefix checks. Exact/overlapping numerical roots remain unsupported.

The separate result subtype is deliberately refused by legacy record restore,
audit, service and continuation paths. Packet-specific persistence, independent
record auditing and application integration remain unfinished.

Source regression: **323 passed in 792.65 s**, including the actual water
default-policy test. Its saved `legacy-native-depletion.json` reports `passed`
and explicitly identifies a manufactured solid, not a sludge material. The test
has an internal 600 s integration limit; this regression command did not impose
a separate per-test external watchdog. Installation regression: **61 passed in
3.00 s**, run from `/private/tmp` without `PYTHONPATH`. The 67 imported installed
modules matched source bytes. Logs and identity are retained alongside this file.

## Actual four-cell experiment

The preregistered experiment preserves the earlier four-cell case and complete
initial state, original 512 attempted-step / 800 s internal limits, original
physical parameters and all scientific tolerances. Only the explicit ordered
policy is added. A separate subprocess supervisor enforces 840 s externally.

The process terminated with exit 0 after **39.018 s**, meaning diagnostic capture
succeeded. **The integration failed**, with
`correction_exceeds_evaporation_fraction`: 13 accepted ordinary steps, final time
0.500262030378867 s versus the requested 0.50032 s, 132 evaluations, 15 attempted
steps and **zero committed packets/events**. The first refinement failed before
any endpoint comparison. The speculative event state was not committed.

This is neither a completed four-cell depletion trajectory nor spatial
convergence. Preserve the failure and diagnose its correction/clock accounting;
do not relax the evaporation-fraction gate.

The independent standard-library audit in `prefix-audit/` checks the 13 saved
prefixes against the original local/cumulative N/E/stretch and component
budgets. Maximum global ΔE + external-pressure work − boundary/body input is
6.166889743e-11 J; accumulated absolute cross-cell constraint-work sum is
1.854993883e-20 J, both below the original 2e-8 J global target. Root reviewed
the saved-data arithmetic; the script's packet branches were not exercised by
this zero-packet result and are not certified by this run.

`numerical-audit/REPORT.md` confirms that no event comparison or independent
approach gate was reached. Crucially, the failed writeback's numerator,
evaporation denominator, selected cell and discarded root frames were not saved.
The source/cost pattern suggests failure during a subsequent speculative event,
but cannot prove its numerical cause. The next bounded implementation should
retain already-computed failure inputs and root evidence without extra EOS
evaluations or state commits, before repeating this specific native diagnosis.

The full Goal remains active: an evidence-complete original-sludge material,
three public mechanism comparisons and heldout prediction, the complete
wet-to-fired/cooled cycle, full spatial convergence and end-to-end application
acceptance are still required. Synthetic tests and native water calculations do
not replace those requirements.
