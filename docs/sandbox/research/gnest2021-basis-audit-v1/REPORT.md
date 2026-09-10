# GNEST basis and inference audit

Read only the already saved 35-page publisher accepted manuscript, SHA2563b49eae9d37fb2fab1c9097b2c5b2606e9ecbfe60e52f639f6e9ae637b78d536. No new download/search, EOS, curve extraction, fitting or edits to committed tables. Original location: https://journal.gnest.org/sites/default/files/Submissions/gnest_03738/gnest_03738_draft.pdf (DOI10.30955/gnj.003738). PDF/printed page numbers coincide in this version.

## What each number represents

1. §2.1 p7: El Salitre anaerobically digested feed was dewatered, predried/crushed, quartered to1kg, dried105°C/10h, milled/sieved0.18–0.25mm. This describes within-study sample preparation, not an identity link to Areias/Arlabosse. Table2 pp7–8 gives moisture as-received66.7±0.5wt% and as-determined9.9±0.2wt%; ultimate/proximate results marked d are dry basis. Glossary p30 defines ar/ad/d/daf distinctly. Those moisture values are not factors that should be reapplied to Table4 dry-feed yields.
2. Table2 pp7–8 reports three-replication SD for characterization. C/H/N/S are measured by named methods; oxygen is explicitly by difference using ash at960°C (footnote2). The table's final explicit ash-temperature row is900°C, not a separately printed960°C measurement. Do not rename900 to960. From the more precise Table5 CHONS numbers, sum=.5281 and complement=.4719. This is an arithmetic complement, not a newly measured ash observation.
3. §2.3 pp9–11: mass recorded during N2 heating, initial105°C drying until constant mass, final960°C30min hold; extra10K/min experiments end570°C for solid analysis. N2 blank corrects balance force (§2.4 p11). Four gases are inferred from concentration/flow using ideal-mixture behavior. Replication statement <3.2% mass-curve difference is not a confidence interval or full product-recovery covariance.
4. §2.4 p11, Eq2: each yield is product mass divided by initial dry sludge mass. Condensate (water+organic liquid) mass AND elemental composition are by difference at the zone transition. It is not independently measured recovery. The Neves correlation in daf basis is then used to choose its water content; ratios printed at570°C involve feed/organic-liquid C,O,H. Text first mentions C,H,N but the displayed ratios use C,O,H; do not silently resolve this wording. §3.2 p18 gives the calculated18.2wt% water. Tables4–5 pp26–27 hold liquid amount/composition fixed above the transition: a model assumption, not a second product measurement.
5. Table5 lower blocks are yield×product composition on original dry-feed basis. BASIS_ARITHMETIC.json explicitly multiplies all six product contributions for C/H/O/N/S at570/960°C from printed decimals. At570°C, back-calculated liquid compositions lie near the printed values (last-digit differences expected from printed factors); they are not independent closure evidence. At960°C, holding liquid fixed while solid/gas amounts/compositions change gives the recorded residuals. This re-derivation neither overwrites printed totals nor forces equality.

## Interpreting positive H/O residuals

The previous fixed-table algebra remains valid: adding only nonnegative missing PRODUCTS cannot remove already positive H/O residuals. But this must not be promoted to proof of physical element creation. In particular, ash-subtracted “O by difference” is not a measured complete mineral-inclusive input oxygen inventory. §3.2 p18 explicitly approximates mineral decomposition using combustion ash changes and assumes equal mineral loss under pyrolysis. Solid ash is itself calculated by an ash balance (§2.1 p7). Therefore mineral-bound oxygen/hydrogen bookkeeping and the changing meaning of residual ash must be addressed before treating these operational ultimate-analysis fractions as a complete atom inventory.

No quantitative mineral-species inventory or mapping is supplied here that establishes how much of +.0148O or +.0025H kg/kg is explained by those effects. Gas/elemental measurement errors, assumed frozen liquid composition and its original difference-derived correlation also remain possible contributors. Missing reactant-side accounting is different from inventing a missing output gas; this audit neither attributes a numerical fraction nor corrects either residual. The paper itself attributes the high-temperature energy imbalance to mass-balance error (§3.2 pp19–20).

## 2.18MJ/kg is a constrained inference

§2.1 p7 Eq1 computes organic-liquid HHV from elemental composition; the printed oxygen coefficient has a positive sign and is retained as printed. LHV conversion uses2.44MJ/kg evaporation enthalpy. §2.4 p11 places balances at25°C. §3.2 p19 supplies LHV7.77/5.19MJ/kg for the two solids,12.16/24.29 for gas products,33.42 for organic liquid, and inferred2.18MJ/kg feed to570°C. This is not measured reaction calorimetry and not a heating-to570°C transient sensible-energy requirement.

A transparent illustrative substitution of Table4TG3, feed Table2 LHV11.3, and water18.2% of total liquid yields2.249853252MJ/kg, not exactly2.18. It is saved as a non-reproduction, NOT a replacement. Ambiguous water basis, rounded intermediate values and their correlations prevent claiming this substitution proves an author error. No parameter is tuned to recover2.18. Independent solid/liquid species reference energies/Cp and temperature-dependent reaction decomposition remain absent; adding this balance as external heat to already adjusted formation energies would double count.

## Actual deliverables and remaining scope

reconstruct.py and BASIS_ARITHMETIC.json retain exact finite-decimal product multiplications and illustrative energy arithmetic; ARITHMETIC01.log records the executed calculation. Division-derived inferred compositions use Decimal28 precision and are explicitly diagnostic, not certified intervals. Ten element/time rows and one illustrative energy substitution were evaluated, with no model or production imports. Full original PDF/text remains private; no original pages are redistributed here.

Next admissible step needs same-material mineral-inclusive elemental accounting, independently quantified condensate/water composition and recovery/uncertainty, plus consistent thermochemical references. Current evidence supports an operational mass-yield model audit, not a fully closed reaction network or raw-sludge material certification. Uncertainty magnitudes cannot be inferred from the current imbalance merely to make a reconciliation feasible.

## Repository reproduction

The public data directory contains a portable reconstruction command with explicit output directory and optional private PDF SHA verification. Its actual output compared byte-for-byte equal to the first saved BASIS_ARITHMETIC.json; REPRODUCE01.log preserves that run's numeric output. The separate Fraction checker completed successfully (CHECK01.log). These checks establish reproducibility and limited arithmetic consistency, not independent verification of all physical interpretations. Public scripts and records were sent for separate review; no original PDF/text/image was copied into either repository directory.

The final [independent arithmetic review](MATERIAL_BASIS_REVIEW_FINAL.md) passed 110 Fraction checks.
Its actual missing-row counterexample exposed a checker that could accept nine rows while reporting ten.
The final checker explicitly requires the unique two-temperature/five-element grid and all six products;
the original missing-row input now fails, and duplicate-row/deleted-product controls also fail. Original
data bytes were not changed. CHECK02.log records the corrected valid-data check. The original failure,
old script and corrected control outputs are retained in the material/review groups of the same-phase
[source continuation evidence archive](../source-continuation-v1/REPORT.md#证据归档).
