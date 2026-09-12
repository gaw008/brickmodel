# Cedrone Table 4: a conditional CHONS pool can proceed

**Use one kilogram of the paper's reported, previously oven-dried sample as an explicitly chosen analysis basis.** Its printed central CHONS values define a 0.704 kg operational element pool for restricted TP composition exploration. The paper does **not** establish a fully specified absolute-dry or original-wet-feed ultimate-analysis basis. Do not relabel the proposal as either. This limitation does not prevent a declared conditional TP calculation.

Actual source: Cedrone et al., *Environments* 2024, 11, 210, DOI [10.3390/environments11100210](https://doi.org/10.3390/environments11100210), existing CC-BY-4.0 PDF, SHA `7b7e7fc7a0e2c41971b90cd12f30ac483ae9681f3d7e458b4a005db502f0ae32`. This task read p4 §2.1 and p8 §3.1/Table 4 in text and actual rendered pages. **Table 4**, not Table 1, contains composition; Table 1 on p5 gives DoE temperatures/heating rates/residence times. The p8 prose also has a Table 3 cross-reference, while the displayed composition table is numbered 4. No new source was searched, and no phase or equilibrium was constructed.

## What the source actually supplies

A Central Italy municipal WWTP supplied 5 kg of anaerobically digested, centrifuged sludge with 75.6 wt% water. It was oven-dried at 105°C for 24 h; 500 g was then ground below 0.5 mm and homogenized. The characterization concerns this prepared material, not the original wet feed. The p8 text expressly attributes remaining moisture to incomplete dehydration or air uptake because the material was not stored dry.

| Table 4 entry | Printed wt% ± printed value | Nominal kg per chosen 1 kg basis |
|---|---:|---:|
| C | 36 ± 1 | 9/25 = 0.360 |
| H | 5.3 ± 0.2 | 53/1000 = 0.053 |
| N | 5.8 ± 0.2 | 29/500 = 0.058 |
| S | 1.1 ± 0.1 | 11/1000 = 0.011 |
| O* | 22.2; no ± printed | 111/500 = 0.222 |
| Ash | 29.2 ± 0.3 | 73/250 = 0.292 |
| Moisture | 2.4 ± 0.6 | 3/125 = 0.024 |
| Cl | 0.050 ± 0.002 | 1/2000 = 0.0005 |
| Br | n.d. | Unknown, not measured zero |

Also printed: volatile matter 57.8 ± 0.3 wt%, fixed carbon 10.7 ± 0.1 wt%, and HHV 15.0 ± 0.3 MJ/kg. Fixed carbon is a proximate-analysis category, not extra elemental C to add to the 36 wt%. Although the caption says LHV analysis, this table's calorific-value column is actually labeled HHV. These values do not give a feed formation enthalpy.

C/H/N/S were directly measured with a Macro VARIO Cube on 20–30 mg prepared samples with WO3 oxidant. **O was calculated by difference from measured elements and ash to 100 wt%, not directly assayed.** The source does not report oxygen speciation or a measured partition of mineral and organic oxygen. Cl/Br were assessed by ion chromatography after bomb combustion. Each measurement was repeated 3–5 times; the checked text does not define the printed ± as SD, SE, a confidence interval, or a hard bound, and gives no covariance. Keep these exact printed qualifications. No independent O uncertainty can be inferred by treating it as another independent direct measurement.

The ultimate-analysis method and table say prepared/dried sample and wt%; they do not explicitly state a dry-basis moisture correction. Consequently, the first model assumption is that the printed central columns can be used together on one nominal reported-sample basis. This is plausible bookkeeping for the prepared sample, but it is not an independently verified dry/wet basis transformation or a claim that all properties were measured on the same aliquot.

## Exact arithmetic and exclusions

The five printed element masses sum to **88/125 = 0.704 kg**. Adding printed ash and Cl gives **1993/2000 = 0.9965 kg**. The arithmetic remainder **7/2000 = 0.0035 kg** excludes unquantified Br and may reflect displayed rounding/basis or other bookkeeping differences; it is not a measured unknown material fraction or an uncertainty bound. Recomputing O from the other displayed central columns before accounting for Br would give 22.55 wt%, not the printed 22.2. Preserve 22.2 and the mismatch; do not replace it or normalize the columns to close exactly. The proximate categories separately sum to 100.1 wt%, also not exactly 100.

Treating the elemental columns as bulk totals means residual water's H/O must not be added a second time. Adding a separate 0.024 kg water inventory to the known CHONS+ash+Cl bookkeeping yields **1.0205 kg**, demonstrating that these categories cannot all be independent component masses. The equilibrium input is an elemental pool, not a starting water/species allocation. The 75.6 wt% original wet-feed water must likewise not be added to one kilogram of this prepared material without a separately declared material-balance transformation.

Ash is an operational residue measurement and has no supplied mineral-element vector or Gibbs functions. Hold its nominal amount as an excluded-material indicator, outside this Gibbs objective. **Do not allocate its oxygen to the difference-O entry, invent an ash formula, or describe the difference-O value as measured organic oxygen.** Direct total C/S/N are also not partitioned into organic and inorganic contributions: making all their reported amounts available to the selected products while omitting mineral chemistry is an explicit approximation. The p8 text attributes a later TG loss to inorganic decomposition such as carbonate, so exact inert-ash behavior is not established. Excluded ash and model CHONS must not be presented as a chemically resolved whole-feed partition. Cl remains explicitly outside the restricted CHONS subsystem; n.d. Br has no quantitative zero or detection bound.

A true absolute-dry conversion would require knowing whether the ultimate columns already include a moisture correction and how residual water contributes to H/O. Only if the displayed fractions were verified as as-weighed totals, and water w=0.024 belonged to the same representative composition, would a water-only removal imply `xC,d=xC/(1-w)` (likewise N/S), but `xH,d=(xH-w*2AH/(2AH+AO))/(1-w)` and `xO,d=(xO-w*AO/(2AH+AO))/(1-w)`. Simply dividing all five columns by 0.976 can double-count water H/O. No dry pool or original-wet-feed pool is admitted here.

## Smallest executable next step

Use the five nominal masses above unchanged; convert them with **the actually bound Cantera atomic weights**, using `b_e[mol] = 1000*m_e[kg]/A_e`, where the API's numerical A_e in kg/kmol is also g/mol. Keep the binary64 values and their exact Fraction interpretations in the eventual input derivation; do not introduce an unrelated atomic-weight table. This task leaves their values null because it did not instantiate or query a phase. All five resulting b_e constraints, including S, must enter the previously admitted 18-gas+C(gr) TP model. The source mass basis remains one kilogram; do not renormalize the 0.704 kg reactive proxy to one kilogram.

One concrete first run can use **800 K and 100000 Pa**, explicit numerical research choices. This T lies inside the paper's 450–650°C DoE temperature span, but a closed CHONS equilibrium calculation is still not a reproduction of its finite-time flowing-N2 experiments. Do not infer a closed-system nitrogen/carrier inventory from 50/60 mL/min purge flow; any added N2, steam or oxidant needs a separate explicit control amount. Keep Gibbs/atom-balance convergence distinct from material validation. Report species amounts and graphite carbon mass per chosen one-kilogram *analysis basis*, with 0.704 kg nominal CHONS input; neither graphite mass nor graphite plus the ash indicator is a measured char yield.

This advances a real, source-informed **conditional final-composition calculation**. It establishes no initial feed enthalpy, heat duty, adiabatic temperature, kinetics, mineral closure or whole-sludge validation. `POOL_PROPOSAL.json` contains the exact Fraction arithmetic and every printed value/unknown used above; no production data were changed.
