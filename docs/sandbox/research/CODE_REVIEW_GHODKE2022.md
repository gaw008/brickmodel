# Independent review: Ghodke 2022 public TGA evidence

Scope: all nine files in `data/sandbox/research/ghodke2022/`, including the extractor, original workbook/PDF, cached official dataset/file metadata, CSV, audit, manifest and README. Read current staged/unstaged scope; unrelated concurrent work was not modified. Reviewer changed only this report. No new experiment, material fit or runtime admission was performed.

## Findings

No actionable findings for the stated evidence-retention and extraction scope.

The extractor pins the original workbook SHA256, validates its sheet relationship and A–E units, preserves original numeric XML strings and row addresses, and applies only the three stated decimal SI conversions. The original hash makes this a bounded extractor for this exact source, not an unrestricted workbook-ingestion service. No smoothing, clipping, sorting, model fitting, DTA-to-heat conversion or fabricated independent validation was found.

## Independent original-data checks

Used bundled Python `/Users/wanggaoying/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3`, independently reading the workbook with openpyxl and inspecting its XML in parallel with the CSV. I did not import the extractor as an oracle.

- Workbook has `Praveen_UPES` plus an empty `Chart` worksheet. `Praveen_UPES` ends at row 11602, and the exported range A28:E11602 contains exactly **11,575 observations**. The empty worksheet is not another instrument run.
- All **57,875 original A–E strings** match the corresponding source XML `<v>` strings exactly. All 57,875 numeric values also agree with independent openpyxl reads. All **34,725 SI values** match independent Decimal conversions. This totals **150,475 field/unit assertions**, plus 11,575 source-row index assertions.
- Headers independently read as `min`, `Cel`, `uV`, `ug`, `ug/min`. Verified time ×60, temperature +273.15 and mass ×1e-9. DTA and DTG remain original signal/unit columns; they are not silently recomputed or given new SI meanings.
- The time sequence is strictly increasing. Independently counted **930 positive mass steps** and **180 negative temperature steps**, both preserved. First/last TG values remain 10538.5205078125 and 2481.8843994140602 µg; the rounded reported 10.54 mg sample mass has not replaced the first measurement.
- Header B5 is `Sample 14 Feed`; B6/C6 is 10.54 mg; B16 is the original `Gas2: Nitorgen (200 ml/min)`. Program C10:F10 is 35→900 °C, 10 °C/min and 10 min hold. These program values remain distinct from actual measured temperature/time.
- G28 onward contains additional workbook formulas (for example `(D29-D28)*100`). They do not redefine the exported instrument E-column DTG and are not used by the extractor.

## Source metadata, PDF and qualification checks

Recomputed all four manifest asset hashes and byte sizes. The two original files also match the **cached official files API** entries for file ID, original filename, download URL, byte size and SHA256. This is a check against retained API evidence; this review did not claim a new live API acquisition.

The snapshot confirms dataset ID/version `r4tb4nbsbc/1`, DOI `10.17632/r4tb4nbsbc.1`, publication date 2022-05-27, named contributors, related article DOI and CC BY 4.0. Attribution/license links and identification of project-derived outputs are present. The related full article is explicitly not claimed as read.

Independently extracted the complete one-page PDF text. It contains **13 model rows**, with activation energy heading **E, kJ mol⁻¹** and prefactor heading **A, min⁻¹**. They are Coats–Redfern model-fit summaries, not 13 separate experiments. The retained sheet lacks sufficient conversion definition, fitting interval and full model-function context for arbitrary kinetic runtime use; the manifest correctly keeps `admitted_to_runtime=false`.

The workbook provides one measurement sequence, not an independent second rate/batch. Random splitting of its rows cannot supply independent holdout evidence. DTA has µV units without a calorimetric calibration; it is not heat flow or reaction enthalpy. TG has not been silently converted to dry-basis reaction conversion. Complete feed preparation/composition, product mass/element balance, reaction enthalpy and matching brick sintering/mechanics remain outside this evidence package.

## Isolated reproduction

Copied the evidence directory into a temporary `/private/tmp` directory and ran the copied `extract_tga.py` with bundled Python. The regenerated CSV **and audit JSON were byte-identical** to the reviewed artifacts. Repository assets and the extractor were not edited or regenerated in place. Audit references to CSV and extractor SHA256 both match actual files.

## Reviewed SHA256 identities

```text
17378113b2a4666b2cc812566731b5e8e543d49f322916fecc0f17a47473ac75  README.md
70eecd021f6a2a437056aeaea57b34d404336b38c0e967fc19004c70b23046fc  dataset-snapshot.json
5edc12532605b71c050ea6f7726900ce5f5ecd82ffb7ca6df2b407eb7280c25c  extract_tga.py
90bd82fd6ac3db60d8caeacf19f76d2c252e6005fd596306514f34088156122d  files-api.json
151395859e466e94f03a3c31a79e4f515a39cbfec058ad19ea503efee35c72a2  kinetic-parameters.pdf
2e8683ce815ad482671029d78bc4a9348d30315de954bf7aafe8a3f3e1cf90be  source-manifest.json
0fb6ddb752c5ed61b32068d3d2bb8934df61fa804abb5810a6789c521a686c17  tga-extraction-audit.json
1f1080ad080037ef8315be447d04b77b3d6f442da6247c3cda9833cb69d0b2c1  tga-observations.csv
57de3dc8b44cc9dfb13c07fe83b2ae939939eac0ed87a1fc4fb122d8e98b2084  tga-record.xlsx
```

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE for original public evidence retention and faithful extraction. This does not approve the PDF kinetic parameters for runtime, establish independent experimental holdout, or complete a same-material wet-brick parameter pack. No source edits or Git commit by reviewer.

## Final LF-format increment review

The initial hashes and full-data review above remain historical evidence. Before the first commit attempt completed, Git's staged whitespace check rejected default CSV CRLF endings. The original extractor, CSV and audit were retained in `initial-crlf-extraction.zip`; this archive reproduces all three initial hashes recorded above.

Independently verified the final increment:

- The entire extractor byte difference is the addition of `lineterminator="\n"` to `csv.writer(stream)`. No extraction range, unit conversion, field, ordering or audit logic changed.
- `old_csv.replace(b'\r\n', b'\n') == final_csv` exactly; final CSV has no CR bytes. Independently parsed old/final CSV tables have identical headers and all row fields. No need to repeat the earlier 150,475 field/unit assertions because the exact byte relation preserves their content.
- Old/final audit JSON differs only in `csv_sha256` and `extractor_sha256`. All measurement counts, source references, anomaly counts and qualification flags are unchanged.
- The README's added paragraph accurately documents the rejected formatting check, retained originals and LF-only correction. Original workbook/PDF bytes were not changed.
- Ran the final extractor on an isolated temporary copy; final CSV and audit again reproduced byte-for-byte. No repository artifact was regenerated by reviewer.

Final increment SHA256:

```text
6d6b71429a2fadc912a385f8e68dadc8c384f32d44cf4517b3f655ce6eeb308a  extract_tga.py
38bdaee74df0c8aa5b9493fd6ec5779e9ea712c1193e35f056624eed51bc79bf  tga-observations.csv
4ee741f690939e2bbf49b64417c0dde93712698ee98fc5324de1e9f35c384765  tga-extraction-audit.json
46d50891dd2e2def0ddf3589f3819157b4cc9e1f5112c84a338f778bce510d33  README.md
3ba4c6155e42c660bb9ac21f8f8f89fbb7a7a1d061d2715a4c5dbbdd04e67c17  initial-crlf-extraction.zip
```

This review approves the final working files, not the older staged CRLF snapshot observed during review. The final staging/whitespace check remains the root agent's commit check.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — LF-only derived-artifact correction verified; original source evidence and previous scientific qualification limits preserved.
