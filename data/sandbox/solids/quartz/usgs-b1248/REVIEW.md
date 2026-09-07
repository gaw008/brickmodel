# Independent review of the limited USGS B1248 record

Verdict: **APPROVE as a literature-compilation candidate only**. No factual correction was required. This review does not admit a runtime volume model or qualify a brick material.

## Inspected evidence

The reviewer read the archived title/method text, the quartz rows, the four cited bibliography entries, and the local official landing-page metadata. The actual rendered printed page 54 was visually inspected at `runs/sandbox/source-cache/usgs-b1248-20260907/printed54-pdf-index59.png`; the requested `/private/tmp/p54.png` was not present, so the recorded cache copy was used. PDF/text cache bytes match `/private/tmp/usgs-b1248.pdf` and `.txt` respectively.

All four cached assets match the byte counts and SHA-256 values in `source.json`. Form-feed page indexing of the extracted text confirms the title page at PDF index 2 and both quartz rows at index 59: printed page 54 is PDF page 60 when counted from one. The image visibly carries printed page 54. The title, authors, 1967 date, Bulletin 1248 and DOI match the retained source evidence.

## Row and method checks

| Row | Temperature | Molar volume (cm³/mol) | X-ray density (g/cm³) | Unit-cell volume (10⁻²⁴ cm³) | References |
|---|---:|---:|---:|---:|---|
| α-quartz | 25 °C | 22.688 ± 0.001 | 2.6483 ± 0.0001 | 113.01 ± 0.01 | 90, 53, 242 |
| β-quartz | 575 °C | 23.718 ± 0.013 | 2.533 ± 0.002 | 118.15 ± 0.06 | 90, 131 |

Both rows print formula weight 60.085, Z=3, crystal-system label `hex.`, SiO₂ and a natural-specimen asterisk. Their values, uncertainty placement, temperatures and reference numbers match `facts.json`. Decimal arithmetic independently confirms both kelvin conversions and all four molar-volume/uncertainty conversions to m³/mol. Historical printed values were not recomputed or silently replaced with modern constants.

The method text supports the recorded unit-cell-volume/Avogadro/Z calculation and formula-weight/molar-volume density relation. It specifies 1963 atomic weights, historical Avogadro value `(6.02252 ± 0.00028)×10²³ mol⁻¹`, and the 1.00202 older-length conversion with a warning that the factor is too low. It also supports the compilation's reassessment of uncertainty, the standard-error assumption for cell-edge propagation, and the density-error exclusions for formula weight and Avogadro uncertainty. The record correctly avoids asserting an independently reconstructed complete molar-volume error budget.

The asterisk qualification is preserved: natural specimens may differ from the nominal formula while tabulated calculated densities use stoichiometric formula weight. Entries 53/90/131/242 in this compilation match the recorded authors, years, titles and bibliographic coordinates. Those original papers were not read in this review or in the extraction.

## Interpretation limits retained

No measurement pressure was identified in the inspected quartz rows or method; `pressure_pa=null` is appropriate. The method's one-atmosphere ideal-gas reference discussion does not establish solid measurement pressure. The two temperatures differ, so their volume difference cannot be used as a same-temperature transition jump. Neither two isolated values nor their printed errors establish temperature-independent high-temperature volume, a compression/thermal-expansion EOS, strict numerical model-error bounds, modern molar-basis compatibility, or sludge composition.

License status remains unverified; full sources remain in the ignored local cache. This limited factual audit makes no claim about republishing the original assets. Unread upstream papers and unknown pressure are disclosed limitations of the candidate record, not falsely represented as completed verification.

## Reviewed record hashes

| File | SHA-256 |
|---|---|
| `facts.json` | `9e2426e241449ed15a641720574e8c53551e6a73bf18887ccccbbecafaccd48f` |
| `source.json` | `3725f5dd43cb93f3ae6d115e89934333e85e3edf6651e0489ec90d10a44edcaa` |
| `README.md` | `5b6a1832127b4ccf24812101b88498c72ffa3afc15e6c93d5aef37bf8b240424` |

Only this review file was added. No source facts, implementation or Git commit was changed by the reviewer; no expanded search or code-test suite was performed.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — limited, traceable factual extraction with runtime and material qualification explicitly false.
