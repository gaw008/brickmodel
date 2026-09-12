# Bounded thermodynamic and numerical scheme review

Decision: approve the proposed interpretation and numerical scheme for implementation, subject to the contracts below. This is not yet a review/approval of `arlabosse_desorption95.py`; code is pending. No production files were changed.

The original [Hack 2011 IUPAC paper](https://publications.iupac.org/pac/pdf/2011/pdf/8305x1031.pdf), DOI 10.1351/PAC-CON-10-12-06, was independently opened with the web tool. Its parsed PDF text at printed p.1033 explicitly relates chemical potential to the reference potential by RT ln(activity). Review modality is actual parsed original-PDF text, not PDF-page screenshot viewing. No Gold Book or Green Book reading is claimed. Only this stated identity is used from the paper.

For the activity derived from Arlabosse's conditional dynamic source method, returning `mu_minus_activity_standard_state_mu = R*T*ln(aw)` is an appropriate source-derived transformation at the reported 95°C label. Its unit is **J/mol water**, because R is J/(mol K). It must not be labeled J/kg without a separate sourced molar-mass conversion. The activity's reference state belongs to this definition; no numerical identification with a separate absolute water potential, pressure EOS, wet-storage energy, or pure-water reference has been established. Calling this relative activity shift does not establish independent equilibrium validation of the sludge method.

Only the existing discrete nodes may be queried. At W=0.10, 0.50, 0.60, the Figure 1 activity (and its derived shift) can remain readable while Figure 2 q_total remains unknown. Missing heat does not invalidate the independently visible activity, and visible activity does not supply missing heat. All other W values remain unextracted and may not be snapped, interpolated, or extrapolated into this set. T must equal the declared 95°C/368.15 K condition; no temperature extrapolation or unknown-temperature correction is justified. All activities and their input bounds must be positive before any logarithm is attempted.

The existing `data/sandbox/thermochemistry/sources.json` entry `nist-codata-2022` was read. Multiplying its exact SI-defining decimal k_B and N_A values as rational numbers reproduces the registered exact R=8.31446261815324. Multiplication by exact decimal 368.15 gives RT=`1530484706436557653/500000000000000` J/mol. The numerical calculation should consume these decimal facts without a binary-float roundtrip.

The [Python 3.12 decimal documentation](https://docs.python.org/3.12/library/decimal.html#decimal.Decimal.ln) was directly read. Integer construction is exact, and `ln` is correctly rounded with round-half-even. The adjacent representable decimal values bracket the exact logarithm. Thus for exact positive a=n/d, separately enclose ln(n) and ln(d), convert every endpoint to Fraction, subtract `[L_n-U_d, U_n-L_d]` exactly, then multiply by positive exact RT. This avoids first rounding n/d. The working context must be explicitly selected for both logarithms and neighboring-value operations. Merely inheriting `localcontext()` and changing precision can retain caller-selected exponent limits or Inexact/Rounded traps. Return nominal approximation and enclosure as distinct concepts; ordinary float conversion of rational bounds is display precision, not guaranteed outward rounding.

Because logarithm is strictly increasing on positive inputs, transform the activity lower bound using its numerical lower enclosure and the activity upper bound using its numerical upper enclosure. This encloses the source-raster range with numerical rounding added. Keep it separate from the numerical enclosure at the nominal activity. Neither result includes experimental scatter, method bias, standard-state uncertainty, or temperature uncertainty; `experimental_uncertainty=None` remains necessary. Values of q_total retain J/kg removed water and the existing includes-latent semantics; they are not an additional heat source or a chemical potential.

## Independent numerical check

`NUMERIC_SCHEME_CHECK.json` records 27 checks: nominal activity and both raster bounds for all nine Figure 1 nodes. The independent reference evaluates

`ln(a) = 2 * sum(z**(2*k+1)/(2*k+1)), z=(a-1)/(a+1)`

with 120 terms, entirely as Fractions. All actual a lie between 0 and 1, so z is negative and the finite partial sum is an upper bound. Subtracting `2*abs(z)**241/(241*(1-z*z))` gives a rigorous lower bound on the remaining negative tail. Multiplication by exact positive RT preserves ordering. This reference does not call Decimal logarithms or a source extraction function.

All 27 narrow rational-reference intervals are contained in the proposed 50-digit neighboring-log interval. The numerical interval width is approximately 1.2243877651492461e-45 J/mol for these actual inputs. This is negligible compared with the digitization propagation width, but it is not experimental precision. The high-activity rational-reference widths underflow when displayed as binary floats in the initial check JSON; those displays are not zero mathematical errors. The exact rational inequalities, rather than those approximate width displays, determine the pass result.

Illustrative approximate shifts at the nominal source activity are -2010.09 J/mol at W=0.15, -1117.70 J/mol at W=0.30, and -76.18 J/mol at W=0.80. They are derived examples only and do not add source measurements.

## Required code review focus when ready

- Exact source facts retained; query output cannot silently override unknown q_total or expose a continuous domain.
- Strict finite/type/domain checks for W and temperature, including bool and NaN/Infinity rejection; no nearest-node tolerance that merges distinct input W values.
- Units, standard-state scope, source hashes/locators, conditional experimental meaning, and immutable returned facts preserved.
- Numerical enclosing arithmetic unaffected by ambient Decimal context, exact source-value decoding, or nearest-float presentation.
- Tests validate behavior and independent numerical/source reconstruction, not merely compare the implementation against its own helper.

No code approval is inferred from this scheme review. Material and full-cycle qualification remain false.
