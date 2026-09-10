# Native02 independent saved-result audit

**Completed interval verified: 1/1024 s, four accepted steps, seven attempted trials, three rejections, 47 distinct captured evaluations.** The offline audit passes 1215 assertions. No EOS/model evaluation or trajectory was run. Input SHA256: `033dccd09ed268eeb2ce9570a37d52f66d4eb5da18b68f2f44a89bd01054c4f2`.

Original scientific parameters, initial/max/min steps, endpoint, tolerances, scales and four-step/four-rejection limits are unchanged. Only inner/outer resource limits are 450/510 s. Recorded inner elapsed time is 448.6015223749855 s, close to its resource allowance. Completion must not be extrapolated into a performance guarantee for a longer case.

## Actual trials reconstructed

| Trial | First capture ordinal | Normalized fine-vs-full error | Controlling component (zero-based cell) | Outcome |
|---|---:|---:|---|---|
| 1 | 1 | 7.241745062250023 | cell2 U | rejected |
| 2 | 7 | 0.14746176476868297 | cell2 N2 | accepted |
| 3 | 14 | 3.57575880237467 | cell2 U | rejected |
| 4 | 20 | 0.044031874358762095 | cell2 N2 | accepted |
| 5 | 27 | 1.2267527636140585 | cell2 U | rejected |
| 6 | 33 | 0.0521844340255484 | cell2 U | accepted |
| 7 | 40 | 0.029711127960278343 | cell2 U | accepted |

All full and fine trial states were independently reconstructed from saved rates, including actual Euler predictor states. The controller's downward binary64 duration conversion and the minimum-tail split rule reproduce every subsequent observed endpoint. Trial6 uses half the remaining interval to avoid creating a sub-minimum tail; it is not simply the unmodified rejected-trial controller duration. Exact times and selected intervals appear in RESULT.json.

Each accepted ledger is independently reconstructed using only its four fine-stage callbacks: each exact dt/4 product is rounded, each half's pair is summed/rounded, and then the two halves are summed/rounded. Coarse full-step callbacks are excluded. Same-time callbacks remain distinct and retain their actual input states. Each accepted endpoint validation matches the reconstructed fine state and stored accepted prefix.

## Physical mapping and actual residuals

All 47 captures preserve four actual fluid molar slots, fixed dry kg in bound source storages, total source-solid-plus-fluid U and energy identity. Every liquid/gas/energy face and opposite liquid-vapor phase pair maps exactly from the actual source evaluation. No added phase/chemical cell power appears. Original liquid enthalpy components remain present in the source observations.

Every accepted step's local fluid amount and U state-minus-ledger residual, and every cumulative prefix residual, is checked against the original policy. Shared internal faces cancel; global water/U residuals equal the sums of actual local residuals rather than being assumed zero.

- Total stored water change: -3.909078118095183e-7 mol.
- Total stored U change: +0.07691197964595631 J.
- Global water state-minus-external-ledger residual: +2.241232924335842e-17 mol.
- Global U state-minus-external-ledger residual: +6.526379371825375e-12 J.
- Largest local amount residual: 4.143126376105227e-17 mol, within original1e-7 mol.
- Largest local U residual: 1.0824029172962213e-11 J, within original .001 J.

Exact rational summaries are in SUMMARY.json. These representation residuals do not replace the temporal full-vs-fine error test, nor prove physical model accuracy. Stored totals are not unchanged: the boundary is open.

## Original failure preserved and auditor correction

PREFIX_COMPARISON.json verifies the first twelve raw capture records are exactly identical to the original failed run. No identity/time/physical normalization was needed or performed. Prior failure SHA is `c9485fc029de2593183f2db5ecaeca1faba3d7c4561691ede9398521c5b85a48`; its original audit remains untouched.

The initially prepared generalized auditor failed at trial20's expected controller endpoint. AUDITOR01.py/AUDIT01.log and AUDITOR02_DEBUG.py/AUDIT02.log preserve that failure and diagnostic. The auditor had algebraically simplified the actual floating computation max_error*q/(1-q), q=1/4, into multiplication by1/3. These are mathematically equivalent but can differ in binary64 rounding. At trial3 this changed the expected controller interval by two least-significant units. The auditor was corrected to perform *.25/.75 in the same numerical order as the integrator. No model data, scientific tolerance or acceptance threshold was changed. Final audit_saved.py and actual AUDIT03.log reproduce every exact endpoint and pass all checks.

Scope: an independent offline audit of a real saved native run and its accepted numerical integration. It does not independently re-evaluate EOS/source constitutive functions, establish measured material qualification, supply transportation-depletion writeback, or complete the full firing model.
