# Final independent code review: finite Areias TG picks

Reviewed the actual untracked `data/sandbox/research/areias2019/tg_digitization/` converter, picks and generated JSON/CSV against the committed calibration. Git staged/unstaged diffs were empty; recent commits identify HEAD `18087a6`. Production files were read only. No EOS, installation or full test suite was run.

No reportable defects found in the current bounded research conversion. The earlier Decimal outward-rounding defect is resolved: cents are computed directly from exact Fraction numerator/denominator with integer floor/ceiling, including negative values. Forty independent adversarial cases included perturbations smaller than 10^-100 around signed integers; all enclosed the original rational. The nominal ties-to-even rounding remains an explicit separate behavior.

Ran the actual command `python3 -B data/sandbox/research/areias2019/tg_digitization/digitize.py --check`: exit 0, `{"targets": 39, "picked": 35, "check": true}`. It reproduces both saved files without writing. Independently reconstructed all 74 populated coordinate intervals (39 temperature and 35 plotted-weight intervals), their eight endpoint/point corners and intermediate-tick residuals using Fraction arithmetic. Each saved lower and upper bound encloses the exact interval with less than 0.01 outward excess. All six endpoint pixel separations exceed two pixels, so perturbed denominators retain sign and the corner extrema are valid for these affine-over-affine coordinate maps. Figure 40 uses its distinct y calibration.

The full ordered 39-target grid survives. Four unknown ordinates remain null in JSON and empty in CSV: Figure 38 at 300 and 400 C; Figure 39 at 300 and 400 C. No interpolation, normalization, reaction conversion, kinetics or material/training admission is introduced. `kinetics_fitted`, `runtime_material_qualified` and `training_eligible` remain false. The stated intervals remain conditional coordinate-picking bounds, not experimental confidence intervals or enclosures of the entire curve across the horizontal interval.

The actual replay checks the source PDF and three native-image hashes, calibration binding, figure/target order, exact nearest-column mapping, selected RGB tuples and selected footprint fit. Independently matched all six upstream hashes in the generated JSON to their current files. Image identity, complete footprint enumeration and semantic unknown decisions still require the separate native-image review: the converter deliberately checks recorded manual evidence rather than claiming automatic scientific approval. This review does not independently establish sample provenance from the original Portuguese thesis or physical model validation.

Review-time SHA256:

- digitize.py: `a5d77579d14dee2ecfba24f253d4f3f50390e269c2e077e00e277f2b9324ac05`
- picks.json: `47abe70a2f8815c361a0ca8eb77682906248113e69320347c9aa54756e43d737`
- points.json: `6967c14e74e9ebd7d04a98638f4e32c71521a36b6f1f259369c248d46cf6ed46`
- points.csv: `8d1ea444a4e72e94b6574d1042d4b623dfbf082d29278cd016f1be51732a6f6a`

Independent arithmetic result: `final-review-probe.json` in this review directory.

## Additional tests and visual-artifact replay

Also reviewed the subsequently added `test_digitize.py` (SHA256 `91a66ce0bf80e80404d3c00d7398223f3b328db14961bdff78d85f1573e9bd33`). Its four tests cover the actual inward-rounding regression, preservation of exact cents, signed nominal ties-to-even and an analytically known coordinate box. Ran `python3 -B data/sandbox/research/areias2019/tg_digitization/test_digitize.py`: exit 0, four tests passed. No substantive defect found.

Read-only review of temporary `render_review.py` (SHA256 `5ae3521447fe7eb96cde45dd07b32b5aadaa5c5a30dc98ac526e28bb8d728706`) found no substantive defect in its bounded frozen-input rendering. It checks fixed picks SHA and source-image SHA, renders diagnostic unknown markers without creating measurements, and performs no RGB selection or modification of points. Ran it with production picks into the separate `/private/tmp/brick-areias2019-tg-final-review-render` directory. All six generated PNG files are byte-identical to the original review PNGs; exact hashes are recorded in `final-review-render-check.json`. This demonstrates replay in the current Pillow/font environment, not cross-version binary reproducibility or independent visual acceptance.

## Final production-renderer relocation delta

Reviewed the exact diff between the previously replayed temporary renderer and the new formal `data/sandbox/research/areias2019/tg_digitization/render_review.py`. Its only behavioral addition is optional `source_directory` / `--source-directory`: it relocates the native-image lookup using `source.name` beneath the explicit directory and retains the original picks and image SHA checks before rendering. Existing default lookup and all rendering operations remain unchanged. No substantive issue found. Approved final renderer SHA256: `f6091d11696dfb478d59385d11407e1a94a4626e28b1311204ad183ad2a57992`.

Inspected root's actual relocation-run evidence `root-render-check.json` and independently read all six output files, matching their recorded sizes, SHA256 values and bytes against the frozen worker renders. No prior arithmetic probes or test runs were repeated for this lookup-only delta.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE the current finite source-bound conversion and exact saved-file reproduction. Separate visual/source review and physical validation are outside this approval.
