# Independent numerical evidence review

Accept the saved bounded numerical evidence; no new EOS, tests, source or installation changes performed by this reviewer. The installed depletion trajectory is outside this audit and was still pending when assigned. Do not infer its success from these checks.

The baseline probe contains 12 temperatures with 11 passes and the retained coexistence failure at 299.9996124454831 K. Its supervisor exit is 1. The candidate probe contains 12 passes and exits 0. Independently recomputed every successful row's density, native h/u/Ts and cp/cv comparison against the saved Python reference using the script's unchanged thresholds. Baseline and candidate kernel identities differ as recorded; the frozen candidate kernel is 88bbbdd91fbe12d351faf6415883c177fec2fec4a7e51d77d98d864b49d51d93. This is a selected nearby-temperature and endpoint probe, not broad-domain convergence proof.

The six-temperature, five-state grid contains all 30 successful rows. Independently recomputed all six saved differences and checked density 2e-8 relative, max h/u/Ts 0.002 J/kg and cp/cv 1e-5 J/(kg K) gates. The grid script's initial Python saturation call is outside the per-case try; no such failure occurred here, so this completed dataset does not prove unconditional continued recording after every possible failure.

The seven derivative cases retain the production case coordinates and finite-difference steps. Recomputed all 21 central differences from saved +/-T and +/-P native snapshots, using the saved public molar mass and common energy offset. Every difference exactly matches the saved value. Independently checked stricter expected-value scaling max(abs_tol, rel_tol*abs(finite_difference)); all 21 pass and exactly reproduce derivative-expected-scaled-audit.json. The script itself uses symmetric math.isclose; the independent audit closes that distinction for these actual values.

Reviewed the 17 recorded stub checks (9 transaction, 8 actual-public-route AST tests): all pass and their kernel SHA matches the frozen candidate. They cover pre/post content and whitespace changes, pre/post configuration changes, warning rejection, nested transaction read counts and public routes. These are no-EOS guard tests, not native EOS failure coverage.

Actual installed-related-tests.xml has 192 testcase elements, zero failures/errors/skips, 1.472 s, and its SHA matches installed-identity.json. All 41 recorded actual site-packages module files independently rehash correctly and are byte-identical to repository src. The new full-suite field is explicitly not_run_on_new_source; the prior source's full-suite result is not transferred to this revision.

Installed callback supervisor completed/exit0 in 1.952220917 s; every input matches before, after and current bytes. Compared the original and new callbacks directly using all ten listed fields: initial amounts/energy, inverse policy, layout, rate, temperature, total-energy residual, total/five-part powers and reaction sources are exactly equal. Implementation descriptors differ, as required for the new kernel identity. This verifies the unchanged callback, not a depletion event.

Historical baseline/candidate/grid/derivative supervisor inputs match their recorded before/after hashes. Current repository and installed kernel/wrapper/manifest/source changed during the declared application; original bytes match production-before copies. One additional baseline input, test_backtracking.py, subsequently changed and no old copy was identified in this audit. It is not the executed probe entry point; retain this provenance limitation rather than claiming all historical inputs remain byte-identical today.

Hashes of audited evidence:

- baseline-probe-result.json: `7a0df5594738ec12000d315cd479e75904c5f7dd4114fbe9900d9e331f550108`
- candidate-probe-result.json: `706afcc7394415718968c3b9a98ada5a8c3d42577ddd206c5f6846710270ec88`
- grid-result02.json: `bcff21b52ce9ee526066e134dc922d80a0c8317b3dac75ce0f07dcea4daac007`
- derivative-result.json: `72f0753bb94285e651530f0a06069cc4db9008e3e772c90cdda8dbd0d575c60c`
- derivative-expected-scaled-audit.json: `45dfca82eacfb60fabb85a0d339ea113987d00ed3d99ed1608a137883c5ba164`
- review-fault-results.json: `e0a4fd9627ef47c1d6c6b8b5e108bf1dcffe9d57a9c04b77396f124fcca0583b`
- installed-related-tests.xml: `c71450667a2d0507edd7d66ac6c99c27ddf0f93df485f4508d9c5a0a19550fe8`
- installed-identity.json: `89f56d1207bef752ce368b7ee153829d6a7be1608f98b65753ce4ea9eccabdb5`
- installed-depletion/callback-result.json: `6addec964d4250f77bea9a6cc62f4de106615552db2d688c9060c39bdda79e6f`

## Installed combined depletion: final result audit

The formerly pending run is now complete: supervisor exit 0 in 57.216599 s, internal completed in 55.630851 s, 182 evaluations, 22 attempted steps, 14 accepted ledgers and 15 states. Exactly one event occurs at 0.5002843906225883 s; accepted continuation reaches 0.5078125 s with liquid zero and the depleted-no-nucleation interface. This actual result supersedes the pending status above, not the retained earlier kernel's failed run.

Independently checked all supervisor before/after/current input hashes. The new depletion.py is byte-identical to the original failed experiment's script; integration policy, event policy, inverse policy and dependency versions are equal. Initial physical inventories and energy remain unchanged, while the implementation-bound energy identity intentionally changes with the kernel. No physical tolerance was relaxed.

Recomputed every accepted step and cumulative prefix with Fraction, including all four inventory columns, closed face fluxes, opposite phase reaction sources, immobile solid/carrier inventories, energy identity, nonnegative inventories and five-part mechanical work. The represented five-part sum plus its saved residual equals each total work exactly; the cumulative absolute component residual and saved cumulative inventory/energy totals also match. Maximum per-step energy residual is 2.297053172672925e-11 J; cumulative energy residual 5.5144477507335457e-11 J; water-sum residual 1.6212740006039342e-22 mol; four-column ledger residual 1.4889251025954498e-22 mol. Original energy, water, H/O and mass budgets are met.

The single event correction removes exactly 5.043154758613299e-20 mol liquid as an ideal negative increment and adds the opposite ideal vapor increment. Actual vapor-before/after difference reproduces its saved Fraction; signed writeback roundoff is -3.3087224502121107e-23 mol and absolute roundoff is 3.3087224502121107e-23 mol. All three cumulative correction/roundoff totals match exactly. The corrected terminal state and terminal ledger match the event record. Liquid remains zero through the two subsequent accepted continuation panels.

The original correction limit includes local ULP allowance plus explicit numerical clock inventory residual. The reviewer initially checked the local allowance alone and corrected that audit assumption after reading the existing implementation; the actual combined gate and absolute/fraction/neighbor-half-spacing limits pass. No production rule was changed.

Saved refinement differences meet the original time 1e-7 s, amount 1e-10 mol, energy 1e-6 J, temperature 1e-5 K and pressure 1 Pa gates. The result retains coarse/previous/final event times and comparison differences, but not all coarse/intermediate native observation states: this review checks the saved gate values and accepted-path arithmetic, not an independent reconstruction of every T/P comparison. The final event retains its own rounding evidence.

Conclusion: the actual installed combined prescribed-deformation/active-phase/depletion fixture now completes and its retained accounting passes independent arithmetic review. This is manufactured integrated verification, not a full physical trajectory oracle or material admission. The new full suite remains separately pending. Result SHA-256: `fe9eccf8995e458281f99aa66ece5e807d32e4ffd459188f237b59d5bc22358c`. No tests, EOS, source edits or installation changes were performed during this audit.

## Final installed full-suite completion

The previously pending full suite is now terminal. Independently inspected installed-full-tests.xml: 1135 actual testcase elements, zero failure/error/skipped elements, 517.635 s. Updated identity records session 85070, completed, exit 0, cwd /private/tmp with no PYTHONPATH. Its stored suite attributes and XML SHA exactly match the actual XML: `c3205b5e16574f53b60a3c60c844a24465fbd730b141ab913d8c1447446acf39`.

After completion, independently rehashed all 41 actual site-packages module files and compared every byte against current repository src. All match both the original module identity entries and the post-suite module comparison list; the frozen kernel remains `88bbbdd91fbe12d351faf6415883c177fec2fec4a7e51d77d98d864b49d51d93`. No tests, EOS, source edits or installation changes were made during this audit.

The current installed-identity.json SHA is `719973733bb6625b3974b8ae69b0f57cccb0b77e188778589ea76129070962d1`. This intentionally differs from the earlier hash listed above because full-suite completion and post-suite byte evidence were appended. Earlier pending statements describe earlier audit time and are retained as history.

Final disposition: the reviewed backtracking revision has independently checked bounded numerical evidence, a completed manufactured combined depletion case, and a verified passing installed regression suite. Scope limits on material admission and independent physical trajectory truth remain unchanged.
