# Independent audit: unchanged wet experiment after pressure-bound correction

**The pressure comparison gate now passes; the actual joined trajectory still fails its unchanged wall limit before an event is accepted.** This is not event-converged or completed wet validation.

Read the terminal v2 depletion0-attempt01 records and v2 full result, then independently compared them against preserved v1 bytes. No EOS, callback, trajectory, test or installation was executed. Production/scripts/PLAN were not changed. The full installed suite remains separately managed by root; this review makes no claim about its outcome.

## Authoritative result and source identity

Supervisor: failed, child return code 1, elapsed 121.72454174999439 s. Inner run: resource_limit / wall_time_limit, elapsed 120.02882358399802 s, 325 evaluations and 38 attempted panels. It retains six accepted steps ending at 0.5002341642497935 s. There are zero committed events and corrections; interface remains existing_liquid with coefficient 1e-6.

Independently matched all 173 actual supervisor input hashes before/after and rehashed every referenced current file without drift. The result SHA256 is `103e737c1ccbf4ec237972832412498e99dbd9b386263eeada1c3967bdde4f3a`. Input count is the actual manifest count, not an estimate based on prior runs. Machine-readable audit: v2-wet-independent-audit.json.

## Exact correspondence with the preserved failed v1 run

Initial state, integration policy and event policy are identical. All committed timestamps, full states (including energy identities), full accepted StepLedger records, cumulative species/energy quantities, correction totals, and cumulative component residuals are exactly equal as parsed data. Therefore the fix did not alter the nominal committed prefix in this experiment.

For completed speculative levels 0–3, start/common/event times, terminal caps, statuses and evaluation counts are identical. At levels 1–3, all four nonpressure comparison metrics (time, amount, energy, temperature) are exactly equal. Only the fifth recorded comparison metric changes:

| Level | v1 pressure metric Pa | v2 pressure metric Pa | Unchanged amount metric mol |
|---|---:|---:|---:|
| 1 | 1.6033257416027111 | 0.006066645497636029 | 5.579376084445943e-9 |
| 2 | 1.6024446977678064 | 0.0051855964477797575 | 1.7686775075932953e-9 |
| 3 | 1.6021777617894093 | 0.00491865841757453 | 6.141210976166531e-10 |

All three new pressure metrics pass the unchanged 1 Pa limit. All three amount metrics still exceed 1e-10 mol. Their time, energy and temperature metrics pass their original gates. Level 4 runs out of wall time without a complete comparison; its partial evaluation count differs because wall-clock scheduling is not deterministic.

The result does not retain every rejected speculative nominal pressure and separate provider bound. Consequently the stronger statement that *each hidden nominal pressure is independently shown unchanged* is not supported by the archive. The exact accepted-prefix equality and exact four nonpressure metric equality, together with the source-only error-bound change, support the narrower finding above.

## Independent accepted-prefix arithmetic

Recomputed each species cumulative increment, local reaction pair cancellation, each Fraction component sum residual, cumulative absolute component residual, closed face fluxes, carrier identity and every accepted E prefix. All match the actual recorded cumulative ledgers. Maximum residuals are C 1.2053617652607596e-16 mol, water 9.595295105615121e-23 mol, analytic A 2.220446049250313e-16 mol, E prefix 1.7920981904939563e-11 J, and per-species prefix 1.205336354272342e-16 mol. All satisfy the unchanged prefix gates. Liquid is positive at every retained state, consistent with no committed event.

The local pressure enclosure therefore removes the demonstrated conservative pressure floor without altering these accepted states or relaxing inputs/gates. Remaining work concerns amount/event localization convergence within the original resource budget. The opportunity and required instrumentation are documented in NEXT_EVENT_SCOPE.md; this review does not authorize dropping unequal-event-state comparison or replacing roundoff evidence with a truncation correction.
