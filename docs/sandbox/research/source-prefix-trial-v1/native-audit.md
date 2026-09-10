# Independent final native trial audit

235 checks passed in0.02647 s against the terminal saved artifact SHA7c0907af104450ffc42cf142e3e3aebefaf21c597eb6806f09b7bdbe6d6d3505. Auditor uses only stdlib/passive JSON/Fraction arithmetic, no source imports, provider calls or new trajectory. Actual outputs are AUDIT04.log and RESULT.json.

All11 actual outer callbacks match wrapper capture state/time/ordinal/output. The3 trial callbacks are genuine first, independently reconstructed Euler midpoint and evaluated prefix terminal. Reference contributes8 callbacks: initial validation, full Heun2 stages, first-half2 stages, second-half2 stages and accepted endpoint. Independent reconstruction preserves net-derivative projection, exact-duration multiplication, both Heun integral rounding levels, accepted state/ledger and original cumulative per-cell tolerances. Actual reference completed1 step,0 rejections on the same exact interval1/16384 s.

Reference fine/full normalized estimator independently equals0.00036442473617906006. The direct cross-method discrepancy independently equals0.001086768806259706 <=1, without division by3. These are different gates; neither is an event-time accuracy certificate.

Independently checked all prefix shared integrals/projections, phase opposition, state/full residuals, positive whole-prefix minima, donor liquid energy, exact Fraction donor projection, total-U decomposition, source identities and unchanged scalar budgets. Original numerical fields and180/210/32 resource controls match the prepared runner. Recorded actual wall/trial durations remain within limits.

Prefix global delta U=+0.012114676166675054 J, delta water=-6.011786913683731e-8 mol. Reference global delta U=+0.012113521705032326 J, delta water=-6.011216509803352e-8 mol. Reference state-minus-shared-ledger residuals are -3.723089544993563e-12 J and -2.2523029583965473e-17 mol. Boundary exchange is nonzero; inventory conservation is not falsely described as zero state change.

Terminal source total pressure uncertainties are0.00128655388515051,0.0013436818095489964,0.0012962428584778825 Pa and include positive available-volume contribution. Exact terminal T/P values and bounds are retained in RESULT.json. This verifies source-record accounting, not an independent EOS uncertainty proof. Every captured material qualification remains false and fixed dry mass stays outside the four molar slots.

Auditor failures preserved: audit01.py/AUDIT01.log initially assumed convenience temperature/pressure properties were serialized directly; actual dataclass stores them in fluid.mechanical. The correction reads those original nested fields, without changing the native result. AUDIT02.log passed217 checks. During adding18 additional global/budget checks, audit03.py/AUDIT03.log preserves an indentation syntax error; final04 fixes only that auditor indentation and passes235. No original model output, tolerance or native run was changed.

Conclusion is limited to one actually evaluated positive numerical source trial and a separately evolved same-interval reference with correct saved accounting. It grants no source dry event, transport-depletion writeback, plant/material validation or arbitrary-trajectory guarantee.
