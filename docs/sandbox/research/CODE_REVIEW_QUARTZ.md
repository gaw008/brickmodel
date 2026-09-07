# Quartz limited-facts independent review

Scope: `data/sandbox/solids/quartz/extract.py`, `facts.json`, `extraction_audit.json` and original HTML in ignored `runs/sandbox/source-cache/quartz-20260907`. This review does not admit a sludge material package or a runtime solid constitutive provider. No extractor/data edits were made by the reviewer.

## Independent evidence

Reviewer used a separate regular-expression HTML table/cell reader and independent float Shomate implementation, without importing the extraction script. Actual `.venv/bin/python /tmp/quartz-review.py` output: 16 coefficient strings, 2 ranges, 19 rows and all 76 printed output fields passed. Each printed Cp/S/−(G−H298)/T/H value was checked within half of its printed decimal unit plus 1e-9 computational allowance; this is formatting precision, not experimental uncertainty.

All 16 A–H strings match the original named NIST coefficient table. Ranges are 298–847 K and 847–1996 K. Original NIST HTML identifies Quartz (SiO2), CAS 14808-60-7 (line339), molecular weight60.0843 (line298 and structured metadata line114), Chase1998 and data last reviewed June1967. The retained mass0.0600843kg/mol is the appropriate g/mol conversion. Original JANAF page lines15–16 give reference298.15K and standard pressure0.1MPa=100000Pa. These values were manually checked against original HTML rather than inferred from the current hardcoded output.

JANAF lines244 and257 retain both847.000K rows: lower-phase Cp76.509, S103.840, H−H29834.196kJ/mol, marker `I <--> II`; upper-phase Cp67.417, S104.700, H−H29834.924kJ/mol, marker `TRANSITION`. They imply printed ΔH728J/mol and ΔS0.860J/mol/K. The two coefficient fits independently give ΔH729.127045576206J/mol, ΔS0.8570688220568456J/mol/K and ΔG3.1897532940577094J/mol. These agree with the extractor's higher-precision calculation within floating arithmetic precision.

The enthalpy jump is a physical transition feature in the retained source. A continuous-gas-style additive offset that forces H continuity would erase the latent transition energy and is inappropriate. Finite fitted ΔG at847K also must remain visible; it is not silently adjusted into exact equilibrium. No molar volume, thermal expansion, compressibility, mineral fraction or covariance was fabricated.

Original HTML hashes independently matched the audit:

- NIST table: `d9c37c3d778299acae5aaa8c9e75105bbd13f777dcfd85d2e7110f9046df42e5`.
- JANAF: `2a1bb000c0223a3227495b9103ae0feb553c4b2c26da721a89c464648c83b728`.

## Initial review observation

The initial extractor compared only Cp/H/S in each printed output row, while the page includes a fourth derived Gibbs-function column. Reviewer independently checked all76 fields successfully and notified root to extend the extractor or narrow its claim. Original identity values are correct for these fixed assets; a future reusable extraction must gate input identity rather than relabel an arbitrary page with hardcoded quartz metadata. Final root manifest and final extractor binding are pending below.

## Final follow-up and binding

Root resolved the initial coverage observation by checking the fourth Gibbs-function column and exposing all four `comparison_columns`. Both original HTML SHA256 values are now mandatory before parsing; manual identity checks above plus fixed asset gates constrain the hardcoded identity/reference values to the actual reviewed files. Reviewer reran the independent reader/formula: all16 coefficient strings,2 ranges,19 rows/76 numeric outputs again passed; no source coefficient or fact change occurred.

Reviewer confirmed current extractor/facts hashes match the current audit. `initial-three-column-check.zip` contains the exact previously reviewed extractor hash `b7b236c2ae6f576c6ee76bba804ccb67d0751423eaf6ff13860b050258e836f2` with its internally consistent audit and byte-identical facts. Historical three-column coverage was preserved honestly.

Final `source.json` and README correctly restrict this to a source-backed pure-quartz standard-state caloric candidate. No automatic runtime loading, stable-domain extension, whole-sludge qualification, density/volume default or transition smoothing is claimed. Original full pages remain ignored: actual `git check-ignore` returned both cache paths. Source URLs and locators identify the original checked NIST pages; this review did not make a new network retrieval.

| File under data/sandbox/solids/quartz | SHA256 |
|---|---|
| extract.py | `73003ef7e9a924b5c12ec15a1ec76b3e1fc86e1e3756ee55b9dd449140a1e0c3` |
| facts.json | `22bdcb839bbd75ed3dfbf6c715326c07688ca535bc2f3767a6ca08bbf87b1025` |
| extraction_audit.json | `cc70cf0209b089faac86e41d85ecb82f0e8cdca426c4b4bc9d69dbd9dc45b89f` |
| source.json | `ea352529863e1ad1a1ce917837940630a1c59f6d609cfb7b23b1fd23678739e0` |
| README.md | `d817c3758c7a1ff4e6f7bd4f32128cee68a3c380e10c465bae32715ddf847eda` |
| initial-three-column-check.zip | `02cd22873d143c8081561183e18f290a42491c722c1e943dcfd3339e4baa3e53` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — fixed-source limited-facts extraction and preserved phase-transition evidence only. No scientific material/runtime admission is implied.
