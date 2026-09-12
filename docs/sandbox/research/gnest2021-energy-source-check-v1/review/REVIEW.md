# Energy-source material evidence review

Scope: the seven new files under energy-source-check-v1 and gnest2021-energy-source-check-v1. Read-only source review, direct viewing of the two existing private page images, relevant private text/HTML checks, and bounded unit-converter controls. No EOS, provider construction, installation, old 66-item arithmetic, original-PDF redistribution or source edits.

The six Cp labels in thesis Table 8-1 visually match facts.json: 1.49, 1.55, 1.51, 1.58, 1.52, 1.48 kJ/kg/K, respectively feed and HRN1–HRN5. The page reports the −10 to 50 °C DSC range and separately adopts 1.52 kJ/kg/K for its model. The record correctly leaves specimen moisture/mass normalization and reported uncertainty unknown and does not treat this as measured high-temperature Cp or reaction heat.

The four ION Figure 7 labels visually match: feed 13110 and 250/550/700 °C chars 14118/8614/8194 kJ/kg, dry basis and 30-minute char residence. Visible error bars were not converted into invented uncertainty numbers. The methods distinguish char bomb calorimetry, composition-derived gas heating values, and experimentally unavailable liquid heating value. Feed characterization refers to prior work. This evidence does not establish a complete reaction-energy balance or the same GNEST2021 material batch.

Both private PDF bytes match the recorded SHA256. Relevant PDF/printed page locators match the private extracts. The thesis title page gives 2016; the repository original bitstream, open-access/CC BY-NC metadata, and ION's 2026-05-13 online date/CC BY-ND metadata are present in saved HTML. Appendix B headings identify products and mass/energy/CHNO tables without establishing a complete mineral inventory. The saved EUBCE page advertises the PDF and the returned page contains login/registration. The CEST access failure is retained as the author's session access report, not independently retried or treated as evidence that no copy exists. No full-text claim or numerical extraction is made for either inaccessible source.

Independent expected conversion values agree with UNIT_CHECK01.json: Cp converts exactly to 1490/1550/1510/1580/1520/1480 J/kg/K; HHV to 13.110/14.118/8.614/8.194 MJ/kg. Initial independent controls passed 8 of 9 cases. They reject wrong Cp/HHV units, wet HHV basis, wrong Cp source, and promotions of material/reaction-heat/same-batch qualification. One actual omission was reported: changing the explicitly unknown DSC moisture basis to `dry` was accepted by check_units.py. Original script, changed data and stdout/stderr are preserved in unit-first; this is a checker boundary defect, not an error in the present source transcription or unit arithmetic.

The author added only `cp['moisture_mass_basis_explicit_for_DSC'] is None`. Final checker SHA256 is `b0f6861b5874d05d666a30ddace753280e67ce7b5b6f8c46cb34639a6836570b`. The same formerly accepted unknown-basis promotion now exits 1, and the normal control still exactly matches UNIT_CHECK01.json. These two narrow rechecks passed; facts and original conversion results remain unchanged. The finding is closed; no other substantive finding remains.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | original one-field finding closed |
| LOW | 0 | pass |

Verdict: APPROVE — factual source transcriptions and bounded unit conversion, with no material or reaction-heat qualification.
