# Independent v4 numerical execution review

Decision: APPROVE the frozen v4 sequential execution plan with its existing stop-on-failure gates. No EOS, test, provider import or source mutation was performed by this reviewer. Only this report was written. All five scripts parse.

## Exact delta and qualification

Independently compared fixture.py, callback.py, depletion.py, compare.py and run.py with v3: all five are byte-identical, and each actual SHA256 matches prepared_script_sha256 in v4 PLAN.json. Comparing parsed PLANs shows changes only to experiment/provenance/execution metadata and the explicit EOS numerical-change description. All physical parameters, source uncertainty declarations, host inverse brackets, integration policies, event gates, prefix ledger limits and resource caps are unchanged. Existing nested ordinary-spine and certified pressure-enclosure policies are preserved.

The current repository kernel SHA is c1ecb59c702382c78891f4fcf6b6ac5eb8c68cc57869b1e261ec8a3a4a796b12 and current approved-manifest SHA is 5f9e39bf1d3376b931caaf8fbda478b482cafe4c8b57a490860ac6ed080bf6db; both equal v4 PLAN pins. The manufactured A/B chemistry, imposed smoothstep geometry and interface model remain explicitly labelled manufactured. Active water remains bound to the approved actual provider; no independent wet temperature oracle is claimed. Legacy v1 labels inside unchanged scripts are explicitly distinguished from the v4 experiment directory/PLAN identity.

## Actual prerequisite native evidence

Read baseline-native-tests.xml: nine tests, one failure, zero errors/skips, 1.046 s. The single failed case is exactly 295 K / 53692.54782795906 Pa with heos_tp_not_converged. Read candidate-native-tests.xml: nine tests, zero failures/errors/skips, 1.031 s. The baseline supervisor is terminal failed/child 1 (1.478275 s); candidate supervisor is terminal complete/child 0 (1.4650732500012964 s), both with leader reaped and no recorded signal errors.

The actual test parametrization is the preregistered 3x3 grid of T0 +/- 0.001 K and P0 +/- 0.01 Pa. Each calls the qualified public provider, checks returned exact input T/P and liquid phase, matches last actual density to the returned state, checks residual subtraction and the unchanged min(1e-4,rho*1e-7) gate, and limits TP observations to 43. The public call still executes the existing full native snapshot/Table-3 checks. The suite uses a shared qualified provider, so its nine passes are neighborhood evidence in that call order, not nine independent fresh-process or complete wet-trajectory proofs.

## Fresh callback and sequential continuation

During review, root's fresh v4 callback completed. Actual callback-result.json says passed, 1.2057313750119647 s; it contains the new c1ecb59... adapter identity. callback-attempt01/status.json is complete/child 0 at 2.087811707999208 s. This is actual current v4 evidence, not a copied v3 acceptance. No callback execution was initiated by this reviewer.

The callback checks current reaction/storage object binding, transfer and A/B rates, no added reaction/latent power, current geometry, energy identity, inverse residual and temperature bounds. Depletion rebuilds the initial model and requires exact encoded initial equality with the passed callback, preventing substitution of a callback from another implementation identity.

Proceed only sequentially: inspect completed fresh callback, depletion0, inspect full terminal evidence and unchanged gates, then depletion1 only after depletion0 passes, then compare only after both pass. The supervisor itself does not automatically enforce this cross-attempt order; the explicit parent-controlled invocation in PLAN does. It retains callback 30 s and integration 150 s external caps; fixture retains 120 s internal cap and 500 maximum steps. No gate or resource relaxation is authorized.

Depletion preserves the whole run before assertion checks, requires one actual event, dry continuation with positive A-to-B reaction, zero liquid and retained nonzero transfer coefficient. Prefix audits retain exact Fraction accounting plus declared residuals, closed flux, carrier, total-water, A+B and analytic-A limits. The comparison requires both passed inputs, exact initial equality, finite differences and original event/amount/energy/temperature/pressure thresholds. Any failure remains a failed result and stops advancement. The current approval does not claim a successful depletion or comparison outcome.

Final freshness check: independently read callback identities: 35 modules before and 37 after, all 35 common module records exactly equal, versions exactly equal. The only additions are lazily imported sludge_sandbox._heos_kernel and sludge_sandbox.water_heos. Whole-dictionary inequality from these additions is not evidence of source mutation. The new kernel identity and current manifest pins were verified above. Review complete; no depletion result is claimed.
