# HEOS coexistence backtracking: applied repair and combined event verification

This packet follows the retained failed experiment in [deforming-active-depletion](../deforming-active-depletion/README.md). It fixes numerical coexistence iteration; it does not supply sludge constitutive parameters or certify a full firing cycle.

## Applied numerical policy

`PLAN.json` preregisters `NUM-HEOS-COEXISTENCE-BACKTRACK-1`. At fixed temperature, the original pressure/Gibbs Newton Jacobian is unchanged. Trial log-density steps use fractions 1, 1/2, 1/4, 1/8, 1/16, 1/32. A trial must meet both original absolute gates (1e-4 Pa and 1e-6 J/kg), or strictly decrease their maximum normalized residual. All native finite-value, branch, stability, source/configuration, lock and final snapshot guards remain. Invalid native/branch results fail immediately. No artificial h/u/s, inventory, energy or timestamp reset is introduced.

Eight evaluated outer states include the seed. Six trials per transition bound coexistence evaluation at 43 pairs, excluding successful final snapshots. Accepted tuples are carried within the transaction, with no cross-call cache. Failed backtracking is explicit; this is not global convergence proof. Kernel SHA is `88bbbdd91fbe12d351faf6415883c177fec2fec4a7e51d77d98d864b49d51d93`; approved manifest SHA is `ffb53b365cf8e77222b9384403fe4670029f94e7ac46df28a786ad03031f4bf0`. Native build/fluid/configuration are unchanged; source and wrapper bindings reflect the real implementation change.

## Actual verification

- The old installed kernel reproduces the exact 299.9996124454831 K failure: 11/12 pass, exit 1. The candidate passes all same 12 selected temperatures, exit 0.
- Original 30-state grid and seven derivative cases pass. All 21 finite differences also pass independent expected-value-scaled comparisons. These are formula comparisons, not public sludge experiments.
- Seventeen no-EOS transaction/public-route checks pass. Eleven new scripted regression cases pass; they deliberately test control flow using nonphysical responses.
- Frozen noneditable installation: 192 related tests pass in 1.472 s, 41 actual installed modules match source. Full installed suite then completed: **1135 passed, zero failure/error/skip, 517.635 s, session85070 exit 0**. After terminal completion all 41 installed modules were imported again and byte-compared to source; XML and final identity are retained.
- Original callback is byte-identical and its ten compared physical/numerical fields are exactly unchanged. Implementation descriptors correctly differ.
- Original combined deformation/active-phase/depletion script is byte-identical to the failed experiment. New installed run exits 0 in 57.216599209 s, completes 182 evaluations, 22 attempted panels, 14 committed steps and one event at 0.5002843906225883 s. It reaches 0.5078125 s and continues dry without changing the 1e-6 interface coefficient.

Independent Fraction accounting checks all accepted steps/prefixes, five mechanical work terms, closed faces and inventories. Maximum step energy residual is 2.297053172672925e-11 J, cumulative energy 5.5144477507335457e-11 J, water 1.6212740006039342e-22 mol. The single ideal liquid/vapor correction is ±5.043154758613299e-20 mol; actual vapor writeback roundoff is -3.3087224502121107e-23 mol. Signed, absolute and numerical-phase cumulative totals match exactly. The original correction budget includes its explicit numerical clock inventory residual; the audit did not replace that contract with local ULP alone or relax it.

The retained event differences pass original time 1e-7 s, amount 1e-10 mol, energy 1e-6 J, temperature 1e-5 K and pressure 1 Pa gates. All coarse/intermediate native observation states were not saved, so independent review checks recorded refinement gate values and accepted-path arithmetic, not a fresh reconstruction of every T/P comparison. Event refinement is not a global trajectory error certificate.

## Evidence and limits

`original-evidence.zip` retains temporary scripts, raw attempts, old production bytes, candidate, XML and reviews; `archive-manifest.json` lists original relative paths, byte lengths and SHA-256, verified against reopened ZIP bytes. Selected files alongside the ZIP are readable copies. The previous failed trajectory remains in its own committed packet.

Historical provenance limitation: the baseline supervisor listed an additional `test_backtracking.py` input that the worker subsequently expanded from seven to eleven tests. The old test bytes were not retained; before/after hashes inside that baseline run match, and its old XML remains. That file was not executed/imported by the native probe. Do not claim all historical input versions remain reconstructible or identify the later test as the old one.

Code review, applied Python integration review and arithmetic review are independent agents within this task, not external expert certification. This successful trajectory uses source-verified water with a manufactured fixed-solid skeleton, prescribed motion and interface coefficient. Free sintering, real raw-sludge thermochemistry/kinetics/transport/mechanics, the required public mechanism comparisons/held-out predictions, full-cycle application and multigeneration search remain incomplete.
