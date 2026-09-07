# TG converter Python review

Verdict: APPROVE the current conversion arithmetic and fixed-source script, conditional on root completing actual pick/overlay review and generation/check after picks arrive. No substantive security, error handling or numerical conversion defect found in the current inputs. This is not approval of point identities or experiment/model validation.

Reviewed `data/sandbox/research/areias2019/tg_digitization/digitize.py`, SHA-256 `b63f1a1a061696f84363689c642cc6673205601d3267c9d6533461e8e5967202`, and the complete committed preregistration README, calibration proposal and independent-calibration-check JSON. Ran independent Fraction arithmetic and AST parsing only. No generation, tests, EOS, installation or production edits performed. Ruff/mypy/pylint/black are unavailable on PATH. At review time picks were intentionally pending; generation and byte-reproduction are not claimed.

The calculated ROOT resolves correctly to the repository. Output paths are fixed beside the script, and --check reads/compares output text without writing. Only the trusted local source record supplies a PDF read path; the script takes no user-specified path or shell command. PDF/image bytes are checked against their recorded hashes. Output includes script, picks, calibration, source, batch links and thermal-facts hashes, preserving the derivation chain. Exceptions fail explicitly rather than producing substitute observations.

Independently reconstructed all six endpoint affine maps and maximum tick residuals with Fraction: each matches the current calibration exactly, including the distinct Figure 40 y scale. All uncertain endpoint denominators remain positive (pixel span exceeds two pixels). With nonzero ordered endpoint separation the affine-over-affine coordinate expression is monotone in each individual corner variable while the others are fixed; enumerating the point and both endpoint extremes therefore encloses the declared coordinate box. Adding the preregistered intermediate-tick residual and outward floor/ceiling to hundredths is consistent with the stated conditional method. The current rational values have ample precision under the 60-digit Decimal intermediate calculation.

Target order and figure order are enforced. The chosen x column must be the nearest integer to the requested temperature's affine-map location; the actual mapped x and horizontal interval are retained rather than replacing them with the target temperature. Unknown observations require a null ordinate and keep null derived y fields; no interpolation, start-mass normalization, slope/kinetics estimation or source qualification is introduced. The finite image-bound checks prevent off-image pixel values, while green-curve identity and footprint bounds appropriately remain human image-review obligations.

Nonblocking maintenance suggestions: (1) assert that the calibration's redundant nominal slope/intercept equal the values derived from its endpoint ticks before using those fields to choose a target column; they agree for all current inputs, but future edits could otherwise select x using a different map from the reported interval; (2) add explicit parameter/return annotations to the small reusable arithmetic helpers when this one-off research converter is maintained further. Neither suggestion changes the reviewed current arithmetic result. The long generate function is linear evidence assembly with no current silent fallback; no architecture rewrite is requested.

Remaining root-owned checks: inspect every picked footprint and unknown decision against the native green trace, verify overlays, independently recompute the final 39 coordinate rows once picks exist, run generation then --check, and archive the successful output with the preserved preregistration. A --check success demonstrates exact current-file reproduction only, not experimental accuracy.

## Final applied increment review

Verdict: APPROVE the final three-file Python increment. Actual SHA-256 values:

- `digitize.py`: `a5d77579d14dee2ecfba24f253d4f3f50390e269c2e077e00e277f2b9324ac05`
- `test_digitize.py`: `91a66ce0bf80e80404d3c00d7398223f3b328db14961bdff78d85f1573e9bd33`
- `render_review.py`: `f6091d11696dfb478d59385d11407e1a94a4626e28b1311204ad183ad2a57992`

Read all three current files and parsed their ASTs. Independently verified the saved points' complete upstream hash list against current files, and all 39 point status/x/y bindings against actual picks: 35 picked, four unknown, with null derived unknown ordinates. The actual picks SHA `47abe70a2f8815c361a0ca8eb77682906248113e69320347c9aa54756e43d737` matches the rendering script's fixed pin.

The final converter now verifies the pick/calibration binding, original-image binding and preregistered pixel widths, checks each recorded column RGB observation against the source raster, and checks observed y footprint containment. My earlier redundant x-calibration suggestion is implemented. These checks validate recorded pixel evidence; human identity/completeness claims remain human review rather than inferred automatically from a green-looking RGB value.

The previous finite-precision Decimal quantization has been replaced by exact rational integer-cent floor/ceiling. For negative values Python's floor division and negated floor implement the correct directed bounds. Fraction round implements the nominal tie-to-even behavior exactly. No finite Decimal intermediate can erase the 1e-100 offset. The four regression methods exercise this real numerical failure, exact-cent non-widening, signed tie-to-even behavior and a known coordinate-box result. I read these tests but did not rerun them; the root owns their reported four-pass execution.

The optional rendering source directory changes only the parent directory of a frozen source filename and still verifies the complete source SHA before loading. It does not modify picks, perform new selection or reinterpret unknown centers as observations. Output names derive from frozen, hash-pinned picks; CLI paths are explicit local file operations with no shell execution. Rendering still uses the same drawing operations, and I have not independently rerun the root-reported six-image byte comparison.

No new substantive defect found. Remaining inherited lack of type annotations in the one-off converter is a maintenance issue, not evidence of incorrect conversion. This approval covers source conversion and diagnostic rendering, not experimental confidence, kinetic fit, material admission or the overall Goal completion.
