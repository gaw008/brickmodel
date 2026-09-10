# Nylen2024 actual full-text evidence review

Source: https://researchonline.jcu.edu.au/83798/ ; DOI 10.1080/07373937.2024.2407959. The publicly linked PDF was downloaded to this temporary research directory; no raw PDF redistribution or source-code admission is requested. CC BY-NC-ND 4.0 is printed on article p2044. PDF SHA256 `d62e8a552b7dd90051fe498d9a28a1eef6e39642b328e9dbcdcf2c719982b70f`, 2351898 bytes, 13 PDF pages including cover.

## Availability and acquisition

Initial web PDF fetch timed out. Curl sandbox DNS failed, then Goal-authorized network escalation succeeded; download session 65727 terminal exit 0. Local `pdftotext -layout` extraction completed. Article body/methods/results were read, and rendered p2049 Table3/Figure3 and p2050 Figure4 were visually inspected. No particle values have been digitized or fitted.

The cover's actual supplementary annotation is https://www.tandfonline.com/doi/suppl/10.1080/07373937.2024.2407959 (confirmed with pypdf in bundled runtime). Web opening returned a non-retryable URL-safety error, so supplementary contents remain unavailable; no alternative guessed filename or bypass was attempted. Main text references mold Figure A1 and drying-time Figure S2.

## What can be modeled from it, and what cannot

The experiment supports **condition-level** comparisons of moisture ratio, center temperature and surface temperature, with endpoint diameter shrinkage. It does **not** supply same-particle joint mass/temperature trajectories: §2.3 p2047 explicitly separates mass and internal-temperature experiments because the thermocouple perturbed weighing. Internal and surface temperatures can be concurrent, but repeat pairing/raw arrays are not disclosed.

This is an experimental dataset source, not a complete constitutive material source. No Cp(T,X), thermal conductivity, diffusivity, sorption law, latent-heat model, shrinkage evolution equation or parameter table is given in the inspected body. No independent model calibration/holdout split is supplied. Figure3/4 captions do not identify sludge origin, so they cannot silently be assigned to MSJ or CB. Figures8/9 provide more explicit material labels, but moisture-ratio normalization is not explicitly defined in the main text; it must not silently be equated to Wang's dry-basis Mt/M0.

## Direct locators and quarantines

| Item | Actual locator | Interpretation or unresolved issue |
|---|---|---|
| Material handling | §2.1 p2046 | Two Townsville plants; refrigerated 4°C after vacuum sealing, molded spheres; not a Wang or factory brick batch. |
| Gas program | §2.2 p2046 and Table2 p2048 | Temperature/velocity prescribed conditions; inlet-room 23°C/50% RH is not hot-gas 50% RH. Mass sampling periodically bypasses flow for15s every3min. |
| Repeats | Table2 p2048 | Ten conditions; separate columns for internal temperature, surface temperature, mass. Some conditions have only one replicate; zero computed population SD there is not evidence of zero uncertainty. |
| Abstract conflicts | p2044 vs §2.1/Table1/Table2 | Abstract treatment associations conflict with methods; high velocity says2m/s while methods/tables/figures repeatedly say2.4m/s. Preserve discrepancy; use method-defined IDs only with explicit precedence. |
| Composition | Table1 p2047 | MSJ ash+volatile+fixed carbon totals90.2, CB101.3. Bases/closure insufficient for a reaction mass package; do not normalize silently or invent missing oxygen. |
| Shrinkage | Table3 p2049, visually checked | Last CB4cm row gives4→3.62cm yet17.8% diameter shrinkage; direct arithmetic gives9.5%. Quarantine this row's shrinkage mapping rather than choose a preferred value. Other small differences may reflect rounded reported means. |
| Temperature and MR figures | Figure3 p2049, Figure4 p2050 | Legible symbols and error bars; figure origin unspecified. Error bars need per-quantity semantics and digitization uncertainty distinct from measurement SD. |
| Materials/size comparison | Figure8 p2052 | Candidate condition-level checks for explicit MSJ/CB and2/4cm at138°C,2.4m/s. Figure9 p2053 explicitly MSJ for velocity contrasts. |

## Recommended next bounded action

Use this source to demand a spatial temperature field and latent cooling in the next candidate, while separately sourcing material properties. Before extracting curves, register a split based on explicit condition IDs, never on observed fitting errors. Preserve all conflicting values and missing normalization as unresolved fields. A credible benchmark may use temperature-only observations without inventing MR normalization, and later expand once an independent source resolves it. Do not claim that endpoint shrinkage supplies dynamic moving-boundary kinematics or that observed crust proves a unique transport mechanism.
