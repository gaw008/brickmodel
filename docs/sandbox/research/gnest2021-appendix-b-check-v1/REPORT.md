# Appendix B: recovered products and limits of calorific-value accounting

The thesis supplies HRN-specific char characterization, selected gas/tar compositions and product energy ratios. It does **not** establish a closed pyrolysis reaction enthalpy. The Appendix B values remain printed observations and derived accounting results; no missing product or carrier-nitrogen inventory is inserted.

## Actual source reading

Mendoza Geney, *Pirólisis de biosólidos en horno rotatorio*, title page 2016, UNAL handle 58938. All four Appendix pages were visually inspected: B1 PDF230/printed213, B2 PDF231/214, B3 PDF232/215, B4 PDF233/216. Chapter7 §7.3–7.4 PDF182–185/printed165–168 was read for recovery and accounting methods. PDF numbers are one-based. The original PDF, extracted text and rendered pages remain private. Source identity, public location and access boundary are in `source-location.json` in the data directory.

The data contain 299 printed numeric cells, retaining decimal precision. `PRINTED_ARITHMETIC.json` contains 32 exact rational sums (12 mass/energy rows and 20 elemental rows), separating sum of printed components, separately printed total, their difference and total minus one. No values were adjusted to close a balance.

## What was measured or derived

- B1: char proximate/CHNO, HHV, BET, bulk density and five selected metals. The table distinguishes dry ash fraction from dry-ash-free elemental/HHV quantities. Five metals do not constitute a complete mineral inventory. Chapter7 refers to Chapter3 characterization; this is not a new reaction calorimeter measurement.
- §7.3–7.4: liquid recovery uses before/after weights of condensation components, with water determined by Karl Fischer on collected tar-system samples. Chromatography determines selected tar composition. Tar HHV is calculated from composition, not an independent bomb measurement here.
- Gas mass combines measured volume, chromatographic composition and ideal-gas conversion. Gas HHV is composition-derived. B2 product fractions are relative to dry-ash-free input; they are not gas mole fractions. HHV entries have MJ/kg-product units.
- §7.4 explicitly attributes mass errors to volatile-phase measurement losses/inaccuracies and proportionally adjusts volatile products before the energy and elemental balances. Therefore B3 energy and B4 elements are not independent tests of an unadjusted recovered-product mass balance. No exact raw-to-adjusted product dataset or uncertainty covariance is reconstructed here.

## Nonclosure retained

B3 printed mass totals for HRN1, HRN1′, HRN2, HRN3, HRN4 and HRN5 are respectively 0.912, 0.901, 0.873, 0.938, 0.974 and 0.986. Their deficits from unity are 0.088, 0.099, 0.127, 0.062, 0.026 and 0.014. These refer to the **printed totals**. Crucially, the independently summed printed components do not always reproduce those totals:

| Row | Component sum | Printed total | Sum − total |
|---|---:|---:|---:|
| HRN1′ mass | 0.887 | 0.901 | −0.014 |
| HRN2 mass | 0.928 | 0.873 | +0.055 |
| HRN2 energy | 0.994 | 1.023 | −0.029 |

These three differences exceed ordinary last-digit rounding of the listed parts. They are source-table inconsistencies, not repaired transcription values. Other nonzero differences of 0.001 are also retained individually. The full B3 page was visually rechecked specifically for these discrepancies.

B4 nitrogen totals for HRN1–5 are 0.074, 0.075, 0.067, 0.178 and 0.437, leaving 0.926, 0.925, 0.933, 0.822 and 0.563 of the input-normalized nitrogen unaccounted in those printed totals. B2 lists no nitrogen-bearing gas species and B4 assigns gas nitrogen zero. Although the apparatus uses nitrogen and GC can detect it, the read pages do not provide a complete carrier-subtracted nitrogen-product inventory. Zero in this accounting table is not evidence that sludge releases no nitrogen-containing gas. Neither N2 nor NH3/HCN quantities may be invented to fill this deficit. Some C/H totals exceed unity; these are accounting nonclosures, not physical creation of elements.

## Why this does not identify reaction heat

B3 energy totals are 0.994, 0.967, 1.023, 1.063, 1.055 and 1.085. They represent calorific-value distribution after the stated correction; they are not reactor heat input or measured pyrolysis enthalpy. Incomplete products, composition-derived gas/tar heating values, reference-state/sensible-heat and water-phase accounting, raw correction details and uncertainty remain unresolved. A product-to-feed HHV difference cannot be adopted as reaction heat without these closures. The low-temperature DSC heat capacities recorded separately in energy-source-check-v1 do not resolve these missing terms.

HRN identifiers support within-thesis correspondence only. Same batch as GNEST2021 or the 2019 retort run remains unknown. No reaction kinetics, full mineral chemistry, material qualification or production control eligibility is granted.

The next useful acquisition is the original HRN run mass/volume/composition worksheets and explicit volatile correction, including gas nitrogen treatment and measurement uncertainty. The existing printed appendix cannot uniquely reconstruct those missing quantities. No additional source search, EOS run or fitting was performed for this task.
