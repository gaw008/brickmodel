# Capone et al. 2025 — bounded source admission review

Reviewed local original paper SHA256 bff7a1e488bdc810a0da0017113c542ef0f0dbb8d6133f68032c57edb8f7b9f0, DOI 10.1016/j.jaecs.2025.100405. UCL repository confirms article identity and hosts the main paper: https://discovery.ucl.ac.uk/id/eprint/10220177/ . No repository/model files or original source files changed. Page numbers below are printed paper pages. Fig. 3 was visually checked in the rendered original PDF (`page8.png`), not inferred only from text extraction.

## Material and experiment identity

§2.1 p3: a bulk municipal sewage sludge from a Central Italian wastewater plant serving 270,000 equivalent people, after anaerobic digestion, post-thickening and dehydration. The actual experimental material SSst was additionally sterilized at 121°C for 30 min and frozen at −24°C to limit biological drift. SSar is the incoming material, not the experimental feed. Do not substitute raw sewage sludge, an Arlabosse sample, or the user's material for SSst.

§2.2: approximately 40 g SSst, Parr 4563 M, 2 NL/min grade-5.0 air, 2 h at each 75/120/150/200/250°C set point; downstream condenser coolant 4°C; three test repetitions per temperature. This is an open semi-batch laboratory operation with oxygen supply and unmeasured gaseous/loss remainder, not a closed constant-volume cell or a resolved time/space trajectory. Supplemental apparatus/procedure A.2 was not recovered in this bounded review. Do not infer sample temperature uniformity, full heat-transfer boundary, pressure program or transient kinetics from a set point.

## Evidence classes

- Measured inputs/outcomes: initial/final solid and condensate masses; oven mass-loss moisture for SSst/SSres (five repetitions); ash by specified incineration protocol (three repetitions); TGA proximate characterization; CHNS elemental analysis; measured condensate analytical channels with stated methods. Mean/95% Student-t confidence intervals describe repetitions, not a complete systematic-error budget.
- Derived from observations: gas-plus-loss remainder `100-rres-rc`, moisture removal and elemental change ratios; SSar moisture inferred via sterilization mass loss; oxygen obtained by difference; fixed carbon residual in proximate accounting. Gas-plus-loss is not separately measured gas yield/composition, and is not an oxygen-consumption or reaction-stoichiometry measurement. With an air-fed reactive system it cannot by itself establish complete elemental closure.
- LHV (§2.3.1 p4; Table3): computed from elemental fractions by the Dulong correlation, not bomb calorimetry or an independent measured heat target. Moisture/dry/ash-free variants share input data; they are not independent validation observations.
- Heat duties (§2.4 p4, Eqs9–14/Fig4): Fermi/order-of-magnitude calculation, pseudo-continuous 20g/h interpretation of 40g/2h, constant heat capacities and latent heat, evaporation at 97°C/0.92bar, and assumed oxidation products. Qdec substitutes standard product formation enthalpies for elemental losses, with CO2/NO2/SO3/H2O assumptions. The main text's enumeration of elements/products/enthalpies is itself not a precise reaction specification; A.5 values unavailable here. Do not reconstruct a quantitative stoichiometric reaction from that list.
- §4.1 p9 explicitly acknowledges full-oxidation assumptions conflict with organic acids in condensate and treats Qdec as overestimating. Neither Qdec nor qtot nor qext is measured reaction calorimetry; even qext remains an estimated engineering heat requirement. These cannot close an unknown actual feedstock reaction enthalpy, kinetics, Cp or caloric reference offset. They may only be stored as the authors' assumed calculation with its inputs/qualifications.

## Table 2: preserve dry-basis reported precision

Original order: (volatile matter, fixed carbon, ash), wt% dry:
SSst (60.8,9.5,29.7); 75°C (58.3,11.4,30.3); 120°C (59.0,12.1,29.0); 150°C (57.7,12.4,29.9); 200°C (54.6,13.9,31.6); 250°C (40.5,22.7,36.8).
Exact decimal row sums: 100.0,100.0,100.1,100.0,100.1,100.0. Preserve values and rounding precision, do not silently renormalize. These are proximate operational fractions, not independent elemental species masses. Do not combine them with CHNS percentages as disjoint material fractions. Ash measured by the distinct BS ISO protocol is 28.2% dry versus 29.7% ASTM proximate; preserve method identity instead of averaging or forcing agreement.

## Confirmed condensate conflicts — quarantine quantitative conversions

Fig3b p8 has an explicit concentration axis mg/l, approximately N–NH4+ 400–1166 and NH3 514–1500. §3.2.2 p6 prints the same magnitudes as g/l: a factor-1000 unit conflict. Store original text and figure separately; a figure-unit interpretation is plausible but must be labeled as such, not silently certified as corrected source data. Do not treat NH3 and nitrogen-equivalent labels as independent additive species inventories.

Fig3c p8 actually labels both axis and legend g/l. Its printed total labels are 13268,1858,884,14997,6106 (75,120,150,200,250°C). The prose instead gives 884–4997 g/l. Thus there is both an unresolved unit issue for an aqueous condensate and an explicit 14997-versus-4997 maximum conflict. No authoritative correction recovered. Do not infer mg/l simply from plausibility or neighboring panels.

Fig3e uses mg/l and marks TC 2195,1033,772,3038,2005; the prose saying above 3g/l at 200°C is consistent with 3038mg/l. Fig3f uses mg/l for both BOD5/COD; these are oxygen-demand assays, not masses of a molecular species or caloric reaction heats. Cross-panel plausibility does not resolve Fig3c's ambiguity.

## What can be held out

A future model of this same prepared material and laboratory protocol can pre-register a temperature-level holdout for final solid/condensate mass, moisture and dry-basis composition, using reported CI plus separately documented digitization uncertainty. Keep all replicas/derived quantities from a temperature together; the main paper has aggregate summaries, not independent per-replicate raw records. Fit at some temperatures then evaluate the withheld temperatures only if protocol/material/boundary inputs are adequate. Until A.2/raw inputs are recovered, these are potential validation targets rather than a ready acceptance matrix.

Cross-material use is qualitative external plausibility only. End-point measurements cannot validate substep dynamics, depletion-event time ordering, mesh convergence, internal temperature fields, or exact local pressure bounds. Fig4 and Table3 cannot serve as independent measured-energy holdouts against a model built from the same elemental data/correlations. Gas remainder cannot validate individual oxidation products. Ambiguous condensate concentration channels should remain excluded from quantitative targets until resolved.

## Bounded supplement search and disposition

See supplement-attempts.json. Exactly three distinct public routes checked: UCL record (only main PDF listed), DOI resolver (tool cache miss), conventional official Elsevier supplement URL mmc1.docx (tool non-retryable unsafe-to-open error). The last filename is a guess, not confirmed metadata. No supplement downloaded, no author contact/purchase, no claim that supplements do not exist. Main article explicitly points to online supplement and says raw data available on request. Current disposition: useful material-specific measured endpoint evidence with traceable derived quantities; insufficient measured reaction-heat/kinetic closure, and unresolved condensate units.
