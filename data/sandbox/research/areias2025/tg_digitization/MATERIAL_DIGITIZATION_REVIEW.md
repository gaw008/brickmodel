# Figure 3 TG digitization review

Verdict: APPROVE for the stated sparse, conditional readout evidence. No unresolved code or data finding. This review does not admit a material model or certify a real brick process.

Reviewed the complete digitize_tg.py, DIGITIZATION_METHOD.md, manifest, CSV/JSON, original Figure 3 page raster and red-circle overlay. Both images were actually viewed, including a full-resolution original. The cached original PDF and raster hashes match the record; the existing Figure 4 points hash matches the manifest. The source's local PDF text supports the figure identities, formulations, pretreatment and distinct instrument protocols.

The 44 fixed targets contain 35 readable and 9 explicitly unknown observations. CSV and JSON agree field for field. The independent standard-library audit passed 356 structural, hash and numerical assertions in 0.024800041 s. It did not import or execute the author's digitizer, change its assets, call a model/EOS, interpolate points or fit kinetics. Its exact arithmetic independently recomputes nominal coordinates, all eight uncertainty corners, internal tick residuals and decimal outward rounding. The stored binary64 interval endpoints also enclose the exact rational envelopes for every recorded axis/readout.

The y axis correctly uses the right-hand TG percentage scale and decreases with downward pixel position; temperature increases to the right. Independent residuals are A: 100/137 °C and 28/333 percentage points, B: 400/549 °C and 24/313 percentage points. The ±2 point pixels and ±1 endpoint-tick pixels are explicit assumptions; the maximum internal-tick residual is added. These intervals are conditional manual-readout envelopes, not experimental confidence intervals or proof of arbitrary between-tick calibration behavior. Shared calibration errors remain correlated.

Visual review found no marker assigned to the DTA branch. In particular, A300/350/450 and B300/350/450 follow the declining TG curve near the DTA crossing; A500/550 and B500/550 follow the steep TG descent; A750/800 and B700/750 track the later mass-loss region; A850–1050 and B800–1050 remain on the lower TG plateau. All 35 plotted markers were inspected against the unmarked source. This visual check does not establish instrument arrays or an exact pixel-center ground truth. The nine conservative unknowns remain null and are not inferred from neighboring values or printed loss labels. Some could become readable with a later higher-resolution extraction, which is not required for this candidate.

A=MIA1 and B=MIA3 are consistent with Figure 3. Both are wall-tile formulations in the publication, with 70/15/15/0 and 70/15/5/10 mass-percent clay/quartz/limestone/preprocessed sludge. Thus the contrast changes both sludge and limestone. The paper describes lime treatment and subsequent beneficiation. Its TG protocol is 25–1100 °C at 10 °C/min; the air-atmosphere statement specifically accompanies dilatometry, so leaving the TG atmosphere unresolved is correct. DTA microvolts are not calorimetric reaction heat. Raw reported TG percent is retained without an invented normalization. Figure 4 provides the same publication/formulation labels, not demonstrated same-specimen pairing. No source numbers have been moved to reconcile the diagram/text mass-loss discrepancy.

The source script deterministically converts explicit manual picks and draws an overlay; it has no solver, optimizer, interpolator or text-label correction path. Its reproduction command is environment-specific and writes the extraction directory, as documented. This reviewer did not execute it. Reproduction/provenance and scientific eligibility remain separate.

Evidence: MATERIAL_NUMERIC_AUDIT.json and audit_tg_readout.py in this directory; reviewed asset hashes are repeated in MATERIAL_DIGITIZATION_REVIEW.json. Original source assets remain unchanged.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — sparse Figure 3 digitization evidence only; runtime material qualification and kinetics fitting remain false.
