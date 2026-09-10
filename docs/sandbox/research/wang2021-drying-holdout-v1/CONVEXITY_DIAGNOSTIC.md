# Posthoc D1 convexity diagnostic

This diagnostic is subsequent to the completed, locked D1 training and once-only holdout evaluation. It changes no parameter, fit, numerical search range, original acceptance rule or recorded residual. It is not a second holdout validation and does not identify the physical cause of a discrepancy.

## Result

For strictly positive observation times, all 7,824 triples across the twelve temperature/humidity curves have nonpositive incompatibility margin. Thus this test provides **no positive-time-only witness** that their expanded pixel envelopes exclude every convex MR curve. Lack of such a witness is not proof of simultaneous feasibility, D1 fit, or model validity.

Including the source-defined MR(0)=1 gives 9,189 triples. Only the 40°C, RH60% curve has positive witnesses (27). The strongest is:

| CSV line | Time (min) | MR center | Original readout bound | Expanded lower | Expanded upper |
|---|---:|---:|---:|---:|---:|
| 127 | 0 | 1.0 | 0 | 0.999999 | 1.000001 |
| 129 | 20 | 0.929231 | 0.015385 | 0.913845 | 0.944617 |
| 137 | 100 | 0.532308 | 0.013846 | 0.518461 | 0.546155 |

Every interval includes the original readout bound plus 0.000001 numerical allowance. Even t0 is conservatively expanded by that allowance; treating the exact model initial value as exactly 1 only strengthens the incompatibility. t0 is still a normalization definition, not a fitted independent measurement.

With lambda=(20-0)/(100-0)=1/5, convexity requires
f(20) <= (4/5)f(0)+(1/5)f(100).
The largest permitted right-hand side is 0.9092318, while the permitted midpoint is at least 0.913845. The exact positive gap is **11533/2500000 = 0.0046132 MR**. It is impossible for a convex curve to lie in all three intervals.

D1 with positive time-independent D and k, uniform initial condition and the same linear boundaries remains a positive sum of decaying exponentials and hence convex regardless of the size of positive D/k or the Arrhenius activation-energy search interval. Consequently expanding those parameter search ranges cannot make D1 match all these intervals while retaining its fixed initial value. This is a structural obstruction at one *training* condition. It does not show that widening the search could never improve RMSE, nor that the original activation-energy boundary hit is explained solely by this obstruction.

The 50°C curves have no positive witness with or without t0. The calculation therefore does **not** establish that convexity alone accounts for the holdout failure or all its out-of-envelope points. It does not distinguish thermal startup, equilibrium moisture, geometry changes, transport laws, digitization limitations or unknown experimental scatter as a cause.

## Method and provenance

`diagnose.py` reads only the original source CSV and the existing training binding. It requires the CSV SHA256 to equal the previously locked **87ba4cccd037a530092720f9ba522eb0eb3710865be769aec5ef39b26e3743cd**, groups by exact temperature/humidity labels, verifies distinct ordered times and the source's t0 normalization method, and enumerates all within-curve triples. No rows are clipped, smoothed, reweighted or removed except the explicit alternative that excludes t0. Time interpolation uses the raw decimal minute values as exact Fractions; seconds and every source row/locator are also saved in each strongest witness. Expanded MR intervals are not clipped to [0,1], making the test conservative.

For every triple (left,mid,right), the exact score is
mid_center-mid_error - [(1-lambda)(left_center+left_error)+lambda(right_center+right_error)],
where each error is original_readout_bound + 1e-6. A strictly positive score is a sufficient incompatibility witness. Result JSON stores exact fractions as the authoritative arithmetic, with floats only as convenient approximate displays. It stores each curve's number of triples, count of positive witnesses and strongest triple for both versions, including negative strongest scores when there is no witness.

Four synthetic controls passed: a decreasing convex rational curve has no positive triples; a deliberately concave midpoint has the exact expected positive gap; unequal time spacing gives the correct zero margin for a straight line; widening errors can correctly eliminate a nominal concavity witness. `run.log` and `result.json` preserve the actual successful execution. The source bytes were compared before/after. No candidate solver or optimizer was imported; no predictions or EOS calls were made.

These are **pixel readout envelopes**, not experimental confidence intervals. The source's actual replicate scatter and correlated measurement errors remain unknown. The witness rejects simultaneous interpolation within these specified envelopes by this convex model family; it does not reject diffusion physics generally, the material itself, or every physically possible drying mechanism. Independent code review of this small diagnostic remains a separate step.
