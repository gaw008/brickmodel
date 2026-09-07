# Independent review: Areias / Maciel / Holanda (2025) finite source record

Verdict: APPROVE as a limited source-traceable experimental-method and figure candidate record. No confident transcription error found in the three reviewed files. Runtime admission, material qualification and training eligibility correctly remain false. This review does not digitize curves or qualify the paper's material for current model prediction.

## Direct evidence inspected

Independently verified all five cached asset hashes and byte counts in source.json against their actual files. Read PDF-extracted pages 1, 3, 4, 7, 8 and 14. Visually inspected the cached rendered pages 4 (methods/Table 3), 8 (Figure 3) and 9 (Figure 4). Also independently rendered original PDF page 3 with pdftoppm into /private/tmp/areias-review-page3.png and visually checked the material pretreatment and Table 1 anomaly. Article page numbers match PDF one-based pages; there is no cover-page offset. The retained original PDF is 16 pages, and inspected page headers/captions identify the stated positions.

The title, three authors, DOI 10.3390/min15080879, Minerals 15 article 879 and publication date 21 August 2025 match page 1. Page 1 carries the authors' 2025 copyright and CC BY 4.0 article-license statement. This is verification of that article statement, not independent rights clearance for every third-party figure or data source. No broader web search or upstream-thesis reading is claimed.

## Material preparation and composition

Page 3 identifies a laboratory wall-tile study using common clay, calcitic limestone, quartz and municipal STP sludge supplied from southeastern Brazil. The sludge is dried at 65 C for 48 h and then mixed/homogenized with 15 wt.% hydrated lime. It is therefore neither sewage-sludge ash nor untreated raw sludge. The precise mass denominator of the 15 wt.% is not separately established by the inspected wording. The earlier procedure is attributed to reference [8], a 2019 Areias thesis listed on page 14; that thesis was not read and its details are not imported.

The subsequent all-material beneficiation at 110 C for 24 h, porcelain-ball-mill comminution and the reported <200 mesh (<75 micrometre) fraction are correctly retained. The mesh notation is reported source wording, not an independently reconstructed sieve specification. Table 3 on page 4 is correctly transcribed in the explicit order clay/quartz/limestone/pretreated STP sludge:

| Paste | Clay | Quartz | Limestone | Pretreated STP sludge |
|---|---:|---:|---:|---:|
| MIA1 | 70 | 15 | 15 | 0 |
| MIA2 | 70 | 15 | 10 | 5 |
| MIA3 | 70 | 15 | 5 | 10 |
| MIA4 | 70 | 15 | 0 | 15 |

Each row sums to 100 wt.%. The sludge replaces limestone while clay/quartz stay fixed; it is not a simple extra addition to an unchanged base formulation. Dry granulation, homogenization and reported 7 wt.% moisture control match page 4. Neither that moisture wording nor the lime pretreatment supports silently reconstructing untreated-sludge dry-mass fractions.

## Atmosphere, specimen and test distinctions

Page 4 gives the STA 409E TG/DTA interval 25–1100 C and 10 C/min but does not explicitly state its atmosphere. The next sentence separately identifies DIL 402 C dilatometry at 25–1200 C, 10 C/min and air atmosphere. Keeping TG/DTA atmosphere null is correct; the latter air statement is not copied across experiments.

The page-4 wall-tile method reports 115.0 x 25.4 x 7.0 mm pieces, 35 MPa uniaxial pressing, drying at 110 C for 24 h, then 1150/1160/1170/1180 C firing for 5 min at 30 C/min and cooling by kiln thermal inertia after switch-off. These are reported specimen-method dimensions, not a measurement of final shrunken dimensions or the separate dilatometer geometry. The dilatometer specimen geometry/probe load and kiln atmosphere remain unspecified in this finite inspected method record. The statement is five test pieces for each formulation; it does not establish five replicates for every formulation-temperature pair.

Figure 4 on page 9 identifies A=MIA1 and B=MIA3. The horizontal coordinate is temperature; the left coordinate is relative length change in percent and the right is relative length-change rate per minute. The printed maximum-rate temperatures 1197.5 C and 1198.2 C agree with the page-8 continuation of the discussion and the two plot annotations. They are reported experimental values, not predictions from the current fixed-geometry model. No raw time/length arrays or digital curve samples were generated here.

## Source inconsistencies and missing evidence retained

The original page-3 visual Table 1 really shows an anomalous CO2 O3 label in the position recorded by the extractor. It is not silently repaired to an assumed oxide identity and is not used to populate a validated composition. Full Table 1 has not been extracted.

The page-8 Figure 3B visible mass-loss annotation is -2.808%, whereas the page-7 prose describes the corresponding event as a mass loss of 2.806%. The facts store their positive loss magnitudes and preserve the disagreement; they do not silently choose a preferred value. Figure A/B identities MIA1/MIA3 and discussion page numbers are correct. This is an internal paper inconsistency, not a data-record transcription defect.

Page 14 states that the presented data are available in the manuscript. That does not establish a separately accessible raw instrument dataset. The record correctly leaves a separate dataset URL and verified raw arrays absent. TG/DTA atmosphere, dilatometer geometry/load, full same-material kinetics/transport/uncertainty and source-chain details remain open; no unreported settings were supplied. Absence claims are limited to the actually inspected article locations, not to every possible upstream source.

The figures can support a future independently specified digitization and held-out prediction study. They cannot establish that the existing fixed-body thermal model predicts shrinkage, nor that these treated sludge/tile conditions represent all municipal sludge or local sintered bricks.

## Reviewed bindings

| File | SHA256 |
|---|---|
| `data/sandbox/research/areias2025/facts.json` | `d4ff122845cb84d478f905bcace557b998d16e37403b61e3a02a7637b21ebefb` |
| `data/sandbox/research/areias2025/source.json` | `35a33684229c2a073b85a4626e2fe0f31c3fa3289856eab305fe3854641a986b` |
| `data/sandbox/research/areias2025/README.md` | `627553c3fc057983ee3fc49050561154203ae20654ec9b913c2efad05ffe672c` |

All asset hashes below independently match their recorded byte counts:

| Cached evidence | SHA256 | Bytes |
|---|---|---:|
| `runs/sandbox/source-cache/areias2025-20260907/minerals-15-00879.pdf` | `9c59141a717cb3b062aed6f28b48ed6005c5564aa3ce5a86de1c083bb6eae8a6` | 8129669 |
| `runs/sandbox/source-cache/areias2025-20260907/minerals-15-00879.txt` | `716536b5f0b24fff8b60b3f30719eebe3a3424cb218061b56c18678400112eba` | 57923 |
| `runs/sandbox/source-cache/areias2025-20260907/page-04-method-table3.png` | `eb4334492969e1e648de9277b48c52b6e01f63ca71c76749e9b344e986126bec` | 298438 |
| `runs/sandbox/source-cache/areias2025-20260907/page-08-figure3.png` | `f5d76f00a1ef2144f795b97055822e8184fa135e96356059d4618cb675b0f01d` | 168563 |
| `runs/sandbox/source-cache/areias2025-20260907/page-09-figure4.png` | `5b16eb1eba1c3385a568d48a3e8dea27d8fa51c7c3896c73084797619457b930` | 185029 |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — limited source record with preprocessing, atmosphere, specimen and internal-figure discrepancies preserved; no runtime/material/training admission.
