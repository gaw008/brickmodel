# Independent source review: Lu 2026 supplement

Result: the six retained MS rows pass transcription and exact-decimal arithmetic review. This is a bounded source extraction audit, not validation of a reaction model or admission of material parameters. No EOS, probes, model tests, installations or runtime source edits were performed. Only this review file was written.

The reviewer independently opened the cached renderings `page-12.png`, `page-13.png` and `page03.png`, read the corresponding table/formula content visually, and extracted pages 12–13 and page 3 directly from the actual cached PDF with `pdftotext -layout`. `pdfinfo` confirms 19 pages and 850466 bytes. The PDF SHA256 is `eada21babd37ae7c17ebcd1aa8b629aa1f753ba9610ac9eb530b5438c013d69a`, exactly matching `source.json`. The title and five named authors match the supplement cover text. The DOI, online publication date and publisher abstract availability were not independently re-fetched in this review.

## Six MS rows

Each temperature boundary, heating-rate label, stage-loss decimal string and total matches the images and direct PDF text. Table S2 is explicitly labelled oxidizing atmosphere; Table S3 is explicitly labelled inert atmosphere. These labels do not specify gas composition or flow. Both Stage 4 table columns show `/` for all six MS rows; the compact retained `stage_4_as_printed` field preserves this missing-stage marker and is not interpreted as a measured zero.

| Table / heating rate (°C/min) | Stage ranges (°C) | Exact Decimal sum (%) | Printed total (%) | Sum minus total (percentage points) |
|---|---|---|---|---|
| S2 / 10 | 50–185; 185–730; 730–1000 | 3.32 + 31.74 + 1.25 = 36.31 | 36.31 | 0.00 |
| S2 / 20 | 50–190; 190–775; 775–1000 | 3.03 + 32.62 + 1.12 = 36.77 | 36.77 | 0.00 |
| S2 / 30 | 50–200; 200–810; 810–1000 | 2.95 + 32.75 + 1.02 = 36.72 | 36.72 | 0.00 |
| S3 / 10 | 50–160; 160–570; 570–1000 | 2.81 + 26.47 + 11.92 = 41.20 | 41.20 | 0.00 |
| S3 / 20 | 50–170; 170–600; 600–1000 | 2.54 + 26.74 + 11.36 = 40.64 | 40.64 | 0.00 |
| S3 / 30 | 50–180; 175–620; 620–1000 | 1.77 + 26.62 + 10.85 = 39.24 | 39.24 | 0.00 |

Python `Decimal` was constructed directly from every retained numeric string. All six computed residuals equal the retained `0.00`; no binary64 rounding, normalization or fitted correction was used. Independently calculated adjacent interval overlaps are 0, 0, 0, 0, 0 and 5 °C. In particular, S3 / 30 prints both 50–180 and 175–620: the 175–180 °C overlap is visibly present in the source, not an extraction error. The sum equality does not resolve that overlap or establish experimental accuracy.

## Printed page S3: equation ambiguities

The visual reading confirms Eq. (S7) contains the coefficient `1.052` multiplying `E/(RT)` with a negative sign. At fixed conversion, its displayed dependence on `1/T` therefore gives slope `-1.052 E/R`. The immediately following prose applies `-Ea/R` to both the FWO and KAS plots. The FWO coefficient discrepancy is real in the printed source. The retained note is accurate and no choice between the conflicting statements has been silently implemented.

Eq. (S8) visibly begins with `G(alpha)=` before the logarithm of `beta/T²`; this extra equality is present in the rendering as well as text extraction. The source note accurately flags it. This review does not repair the equation, infer a missing derivation, or approve an activation energy, prefactor or mechanism. `S3` here means the printed supplement page, whereas Table S3 appears on printed page S13.

## Access and interpretation limits

The cached `publisher-pdf-response` contains the literal message `您没有下载权限` and is not a main-article PDF. It provides no full-text experimental methods. The available supplement and these retained rows do not establish the missing mass basis, sample preparation, gas composition/flow, experimental uncertainty, confidence intervals or chemical product yields. The null fields and false runtime/training/validation flags correctly preserve that limited scope. No material identity link to Areias 2019 is established. Stage-loss summaries do not by themselves determine a unique kinetic network or its stoichiometry.

No redistribution license was verified. The ignored local PDF and images were inspected without copying them into tracked artifacts. No claim is made that the unreviewed supplement figures or remaining kinetic tables have been independently visually checked.

## Reviewed input hashes

- `source.json`: `f6833ac613953864dfe0fceedd8a4a5563d7f889604f74e1538905f013565c95`
- `ms-stage-observations.json`: `59ad4481ec141c104392b55d0da1bc9070b8281b685b0cc12a8d373e5333aa5f`
- `README.md`: `67c8b3c6d48f7f0350d4680bc38433b7ec4d08b7be087486d7cdc84ad8cdf80c`
- `page-12.png`: `6d580890fef11d0728fb76ae74e71ce7acffee613e645009f5cf363d5f68711f`
- `page-13.png`: `9c9d22804fcc4bfd56124af8ab3f8770403943a3582cf7fddc289539d53d24fb`
- `page03.png`: `815727b22059dd4fa6f532b27bde873f06f07d91e5df1d4d2a046dcf11948002`
- `publisher-pdf-response`: `1ee6b30ff95cbaf24c2603a5bcd3c97f718150f5a3be523d99c5fd2e4d0a3691`
