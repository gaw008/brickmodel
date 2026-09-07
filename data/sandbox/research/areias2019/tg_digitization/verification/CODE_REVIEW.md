# Independent code review: Areias 2019 sparse TG coordinate conversion

Reviewed `data/sandbox/research/areias2019/tg_digitization/digitize.py` (SHA256 `b63f1a1a061696f84363689c642cc6673205601d3267c9d6533461e8e5967202`) against the actual tick-calibration proposal and preregistration README. Staged/unstaged Git diff was empty at entry. No production/data/tests were modified, no installs, water EOS or whole suite were run. Picks were not present at review time; this is not a review of 39 visual observations or final generated files.

## Findings

[MEDIUM] Decimal pre-rounding can invalidate outward enclosure for accepted high-precision coordinates

File: `digitize.py:decimal` (lines 61–65).

The rational is first divided under a 60-digit Decimal context using its default nearest rounding, then rounded to cents. The first operation can land on an exact cent from the wrong side. Independently reproduced:

- `decimal(Fraction(1)-Fraction(1,10**100), ROUND_FLOOR)` returns `1.00`, which is greater than the exact lower endpoint.
- `decimal(Fraction(1)+Fraction(1,10**100), ROUND_CEILING)` returns `1.00`, which is less than the exact upper endpoint.

`pixel_y` accepts arbitrary Fraction-parsable strings and does not enforce the finite half-pixel grid used by the manual workflow. Thus the helper's outward-rounding guarantee exceeds its accepted numeric-input contract. This does **not** establish a defect in the pending actual 39 picks: all independently checked ordinary half-pixel coordinates pass. Minimal fix: compute floor/ceil of `Fraction * 100` with integer arithmetic, then format the exact integer hundredths; alternatively explicitly restrict inputs to the preregistered finite coordinate precision. Do not enlarge physical uncertainty to mask rounding.

## Confirmed behavior and limitations

For all six actual axes, endpoint pixel separation exceeds two pixels, so the perturbed denominator cannot cross zero. The linear-fractional interpolation is monotone in each coordinate with the others fixed on this box; extrema occur among the eight endpoint/pick corners. This supports the current corner enclosure, including the reversed green y axes. Intermediate tick residual is recomputed exactly and checked against the preregistration, then added conservatively to both sides. It is not a confidence interval or whole-curve enclosure.

Independent numerical check evaluated 7,206 cases: every half-pixel coordinate from 0 through 600, across six axes. Compared emitted lower/upper values against independent exact rational integer cent-floor/ceil. All passed. Nominal slope was also independently checked from endpoints. Evidence: `review-numerical-probe.json`. This is a finite arithmetic check, not validation of visual identification, unknown judgments or experimental accuracy.

PDF and actual image bytes are hash checked against source/calibration records, and source manifest, batch links, thermal facts, calibration, picks and script hashes are recorded as upstream. Figures/order and exact target grid are enforced. Source attribution is traceable to the local records; it does not cryptographically authenticate externally edited metadata or independently establish the sample-to-figure mapping. Those records and final picks still need the separate source/visual review.

Unknown values require null ordinate and remain null in JSON (empty CSV fields); no interpolation or weight-loss normalization is introduced. Picked coordinates must lie inside the source image. Unsupported status, nonfinite Fraction text, missing required fields and mismatched hashes fail rather than silently fabricating points. Some malformed local schemas raise built-in KeyError/IndexError/StopIteration; this offline conversion has no untrusted service interface and no silent-success consequence was found. Empty reason text is not semantically assessed by the script, so per-point evidence/occlusion reasoning remains a reviewer obligation.

No claim of reaction kinetics, experimental uncertainty, model validation, training eligibility or runtime material admission is made by the output. The fixed endpoint map used to choose x columns agrees with the current tick endpoints; a changed calibration would need renewed review, not a claim that this script independently approves it.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 1 | info |
| LOW | 0 | pass |

Verdict: APPROVE for the bounded ordinary manual-coordinate arithmetic, with the concrete outward-rounding input-contract issue above to resolve before advertising a general rational enclosure. Final 39 picks, source overlays and derived-file replay remain unreviewed.

## Final increment: exact rounding repair and all actual picks reviewed

The first review above is retained as history. The MEDIUM finding is now **CLOSED**: final `decimal` computes integer floor/ceil of exact Fraction hundredths, and nearest nominal values use exact ties-to-even. Independent tests of both ±1 with ±1/10^100 perturbations now enclose correctly in all four cases. No physical envelope was changed.

Final script adds calibration hash, fixed point/tick envelope, per-plot source hash, actual saved-pixel RGB, and redundant x calibration consistency checks. I read the new implementation and independently executed `digitize.py --check`: **39 targets /35 picked /4 unknown**, exact saved JSON and CSV replay passed.

The independent `review_final.py` recalculates all 39 horizontal and 35 vertical coordinate triples using a separate barycentric Fraction interpolation formula, independent eight corners and tick residuals, followed by integer rational cent rounding. Every nominal/lower/upper value matches the actual JSON. All CSV fields match their JSON representation; all upstream hashes, original PDF hash and three native-image hashes match actual bytes. Unknown ordinates and bounds are null at Fig38 300/400°C and Fig39 300/400°C, without interpolation.

For every one of 39 original x columns, I rescanned **every row in the TG plot** using G>R and G>B, including arbitrarily faint green antialias pixels, and compared the complete list of row numbers and RGB values to the recorded footprint. All match. All 35 accepted footprints fit unchanged ±2 y pixels. The three steep rejected columns span more than four pixels; Fig39 400°C remains unknown despite its narrower green-only subset because of visible magenta overlap. The production script checks listed pixels, not completeness by itself; this independent full-column check closes completeness for the present frozen data, not arbitrary future picks.

Initial independent scan mistakenly extended below the TG plot into text/axis labels and detected extra faint green pixels there. The exact discrepancy and scope correction are preserved in `review-scan-scope-note.txt`. Final scan runs from image top through the preregistered horizontal-axis crossing, without any near-picked-y restriction. No source/data were edited in response.

I actually viewed all three complete overlays and all three contact sheets. Accepted circles follow the green Peso trace; Figure40 uses its own 120-to-20 vertical calibration. The four unknowns are conservatively retained as described. Horizontal and vertical conditional point boxes do not enclose an entire steep curve segment, establish experiment uncertainty, or turn plotted Peso into cumulative mass loss/conversion.

Final bound SHA256:

| Artifact | SHA256 |
|---|---|
| digitize.py | a5d77579d14dee2ecfba24f253d4f3f50390e269c2e077e00e277f2b9324ac05 |
| picks.json | 47abe70a2f8815c361a0ca8eb77682906248113e69320347c9aa54756e43d737 |
| points.json | 6967c14e74e9ebd7d04a98638f4e32c71521a36b6f1f259369c248d46cf6ed46 |
| points.csv | 8d1ea444a4e72e94b6574d1042d4b623dfbf082d29278cd016f1be51732a6f6a |

Detailed independent results and all 39 full green-column row lists: `review-final-result.json`. No EOS, installation or full suite was run.

## Final Review Summary

| Severity | Open count | Status |
|----------|------------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | prior finding closed |
| LOW | 0 | pass |

Verdict: APPROVE — frozen 39 sparse TG observation candidates and conditional coordinate conversion only. No kinetic fit, holdout model validation, training or material admission is implied.
