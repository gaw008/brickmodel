# Internal heat/moisture transport: bounded source audit

2026-09-12. Four targeted searches; two new original full texts actually read. No Chavez retry, fitting, digitization, EOS, physical run, production edit or Goal change. Exact retrieval states and hashes are in `SOURCE_ASSETS.json`; original documents remain private here.

**Decision:** no same-Arlabosse-sludge internal transport package was established. There is usable empirical evidence for a declared hybrid exploration, with substantial identity and temperature-transfer errors left unknown. The evidence does not make this hybrid a measured brick material or a validated 1D drying predictor.

## Existing sources

[Arlabosse2005](https://doi.org/10.1590/S0104-66322005000200009), original publisher HTML SHA256 `7dc682647cc70503820e6738b806b052ddccc9f1bc14650178e8813c7e203816`: no sludge internal moisture diffusivity or thermal conductivity law. Eq3 is equipment-normalized contact drying flux. Its coefficients cannot be dimensionally converted into an internal diffusivity by introducing an assumed thickness.

[Ferrasse/Arlabosse/Lecomte2002](https://doi.org/10.1081/DRT-120003755), printed pp752–763: the apparatus steel conductivity and contact resistance belong to the heater; inferred wall-to-sludge heat-transfer coefficients include apparatus/contact effects. The tested anaerobically digested municipal material differs from the 2005 predominantly industrial biological sludge. [Ferrasse/Lecomte2004](https://doi.org/10.1016/j.ces.2004.01.002) establishes calorimetric/sorption measurement, not a matching internal transport law. These two full bodies were previously read through author-uploaded web text; no original PDF SHA is claimed.

## New original 1: effective moisture diffusion

[Mäkelä et al., Water Research91 (2016),11–18](https://doi.org/10.1016/j.watres.2015.12.043), [accepted manuscript](https://orbi.uliege.be/bitstream/2268/192978/1/Mikko_2016_preprint.pdf).

| Fact | Exact location/value |
|---|---|
| Identity | Manuscript p5 §2.1, lines90–97: Swedish paper-mill mixed sludge, 60% primary/40% biological; belt filter/centrifuge; approximately27% dry solids. Untreated control is distinct from hydrochar. |
| Geometry/boundary | p6 §2.3 lines124–139:20mm-diameter compression cell,50N/1min;4.10±0.041g cylinders; entire exterior exposed; air105°C,1.5m/s,0.007kg water/kg dry air. |
| Inference | pp7–8 Eqs1–4: moisture-gradient Fick approximation; `D_eff=−L²/π²·d[ln(X/X0)]/dt`, m²/s; L is full sheet thickness. Shrinkage inferred from endpoint CT and assumed linear. |
| Admissible scalar | PDFp22 Table1 footnote and abstract: untreated mean `8.56e−9 m²/s`; manuscript p10 line210 says `8.57e−9`. Preserve discrepancy; it is not an uncertainty interval. |
| Data | PDFp25 Fig3c–f: mass-time, polynomial fit, dimension ratio and inferred D; not independent validation of that fitted D. |

Original PDF SHA256 `f4200d99c4fa8f3f6585fde9ec2e15455bfa78644a953e52b7311c1df25cba91`,4,442,717bytes. Text read; original PDFpages9,10,22,25 viewed after local rendering. Missing: local sample-temperature history, D(T) activation parameters, uncertainty/covariance, machine-readable underlying series, independently measured conductivity. No hydrochar coefficients are borrowed. The source data below X≈0.053kg/kg dry were discarded.

## New original 2: conductivity measurements

[Septien et al., J.Environmental Chemical Engineering8(1) (2020),103652](https://doi.org/10.1016/j.jece.2019.103652), [original article XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7043394/fullTextXML).

This is VIP pit-latrine faecal sludge from eThekwini, sieved5mm/stored4°C (§2.1), not wastewater activated sludge. Material similarity is limited to unincinerated organic wet solids; it is a more distant donor than the paper-mill control above. C-Therm TCi measurement is described in §2.4; its test temperature is unspecified. Dryer temperature must not be relabelled conductivity measurement temperature.

| Original Table2 row (30% MIR preparation) | Moisture, % wet basis | k, W/(m K) |
|---|---:|---:|
|25min|47±2|0.062±0.002|
|40min|23±6|0.056±0.001|

§2.3.2:3kW emitters,85°C drying-zone temperature,8mm pellets. §2.5: repetition-based Student-t90% intervals. Ten original thermal rows are transcribed in `SEPTIEN_THERMAL_TABLE_CELLS.json`. These are source-sample intervals, not Arlabosse transfer bounds. No internal moisture diffusivity is reported; thermal diffusivity is a different quantity.

Original JATS XML SHA256 `cda0a7fba9cea9dc3b20d8a4b68f36ad571dcaf22deaec7386f323dd95714a0f`,102,289bytes. Full original body/table cells read; no PDF or page-image reading claimed. Filename uses DOI/copyright2019; issue year is2020.

## What can be implemented without inventing numbers

The following is a **reviewer's conditional construction**, not an equation or qualification asserted by either paper:

- Use the Table1/abstract branch `D0=8.56e−9 m²/s` as a frozen donor diffusivity. Record the alternative printed8.57e−9 separately. Freezing it across moisture and35–95°C is an explicit approximation; the105°C drying-air experiment supplies no measured temperature-transfer law.
- The two same-preparation thermal nodes above convert exactly from wet fraction y to dry-basis W=y/(1−y): `W1=23/77`, `W2=47/53`. A declared linear k(W) between `(W1,0.056)` and `(W2,0.062)` supplies positive conductivity without extrapolating nominal moisture coordinates. A restricted nominal W-range0.30–0.80 lies inside these two coordinates. Source moisture uncertainty must remain separate; nominal coverage is not guaranteed coverage of every possible true node position.
- Holding this k independent of temperature is another declared approximation because measurement temperature and k(T) are unknown. Extending below W1, including the existing W=0.15 endpoint, needs an explicitly named extrapolation or a different thermal branch; it is not covered by this two-node interpolation.
- Keep current Arlabosse wet enthalpy as the caloric component and name the complete material **hybrid exploratory donor transport**. Do not call it same-sludge evidence. A conservative spatial mass/enthalpy implementation with independent manufactured conservation/convergence checks would materially add internal coupling; it would still not validate real brick drying time or satisfy full Goal.

A transport interface should expose D in m²/s and k in W/(m K), donor IDs, exact domain/approximation choices, and separate source-reading/source-experimental/transfer errors. For a fixed geometry Fick form, water flux needs dry mass per physical volume: `j_w=−rho_d,bulk D grad(W)`. Neither new source supplies Arlabosse bulk dry density or a brick shrinkage law. Geometry and md/volume can be explicit controlled specimen inputs; they cannot be labelled measured porosity, density or shrinkage of the source material.

No source here justifies equating Fick diffusivity with chemical-potential mobility. Conversion would require the wet-model thermodynamic factor and a stated nonisothermal transport convention; thermodiffusion/cross coefficients remain unknown. Internal water transport must carry the chosen water enthalpy consistently in the energy ledger; surface vapor discharge is a separate boundary term. These are implementation requirements, not additional measured constants.

## Scope of evidence still missing

Same material k/D; D(T,W) at35–95°C; density/geometry evolution; pore connectivity and directional transport; measured heat/moisture boundary coefficients for the brick; native T/W profiles and independent holdout data. The donor mass curve used to infer D cannot also count as a held-out validation of it. No total model-error bar is available, but that does not prohibit the explicitly conditional implementation above.

The closest low-temperature lead, [Font et al.2011](https://doi.org/10.1016/j.seppur.2010.12.001), concerns coupled sphere/tablet drying at30–65°C. Only publisher abstract/section excerpts were readable; complete material identities, tables and parameter conventions were not verified. No parameter from that partial body is admitted. Bennamoun2013 ORBi lists a restricted request-copy file; Arlabosse/Chitu2007 and AlAhmad2021/22 remained abstract-only. Saha2026's PDF URL redirected to an abstract. These are access states, not evidence that the studies lack the relevant physics.

## Permission boundary

Septien original front matter explicitly states CC BY4.0. The Mäkelä author manuscript is openly downloadable under the [ORBi user license](https://orbi.uliege.be/page/user-license), which excludes commercial uses and restricts derivative uses; no broader redistribution/commercial authorization is inferred here. Originals stay in private scratch; no public redistribution was performed. This factual parameter audit does not alter the source documents. Future public source packaging must retain actual license/version attribution and cannot label every asset CC BY.
