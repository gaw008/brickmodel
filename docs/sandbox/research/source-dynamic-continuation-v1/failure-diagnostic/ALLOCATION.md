The numerical failure is localized to wet cell index 2 (the third cell), in both event/common endpoint comparisons. The corrected dynamic code ran no ordinary HEOS segment because its actual parent comparison was not admitted. No retry is authorized by this diagnosis.

The original pressure gate remains 1e-4 Pa. At the event endpoint, the exact saved joint bound is 4.649847818827615e-4 Pa:

| Contribution, both compared endpoints | Pa |
|---|---:|
| Original actual-fluid pressure errors | 3.5498859841684416e-4 |
| Temperature continuation | 1.0616953613374042e-4 |
| Reported pressure to full-box root, including machine residual | 3.7698820787731498e-6 |
| Root difference | 5.676525340353031e-8 |
| Other projection/extra continuation terms | about 2.20e-19 |

The common endpoint has the same pressure/root terms and temperature term 1.0593954072727371e-4 Pa, giving 4.647547864762948e-4 Pa. Removing every temperature term would still leave 3.588152457490211e-4 Pa. Conversely, temperature terms alone exceed the gate. Changing only one solve tolerance is not a sufficient strategy at these saved points.

This is chiefly reducible numerical residual, not a need to shrink declared volume uncertainty. Each cell-2 actual-fluid pressure error is 1.7749429920842208e-4 Pa. The original bound uses declared global compliance 1.0257968254709306e-11 m3/Pa and consists of 1.749439749931228e-4 Pa from |F_saved|=1.7945697418321124e-15 m3, 1.131944270946947e-7 Pa from volume representation, and 2.437129788204521e-6 Pa from the unchanged liquid-volume error envelope, plus outward conversion. The independent derive.py reproduces the final reported binary64 pressure error exactly. Local joint compliance is larger, 9.659636257986174e-10 m3/Pa, but it cannot replace the original required global-fluid term by assertion.

Temperature inversion likewise returned early within its original 1e-5 J energy tolerance. The energy residual magnitude is about 5.196e-6 J, while the retained point energy error is 7.036381333954428e-8 J and minimum heat capacity is 318.54730000002 J/K. Its actual eT is about 1.65327e-8 K. With saved conditional slope 3210.9007076 Pa/K, about 5.23755e-5 Pa per endpoint comes from the numerical energy residual; only about 7.09255e-7 Pa per endpoint comes from the retained point energy-error term. derive.py reproduces the outward eT exactly. The original 1e-6 K temperature stopping limit is inactive here.

A defensible next numerical profile can retain the entire physical case and original event/resource gates, and change only:

- mechanical pressure_tolerance_pa: 1e-5 -> 1e-7;
- inverse energy_tolerance_j: 1e-5 -> 1e-6.

Keep inverse temperature_tolerance_k=1e-6, maximum_iterations=100, eV=1e-12 m3, liquid v error=1e-16 m3/mol, all caloric/derivative errors, initial temperatures, conductivity, transport, and event tolerances unchanged. Keep the old failed case and results immutable; register the new numerical choice separately before any execution.

For a per-endpoint actual-fluid allocation of 2e-5 Pa, the saved global-bound formula allows |F_saved| <= 1.7899822025443035e-16 m3 after retaining all other terms. The proposed tighter pressure stop is a sensible way to target this: finish() requires both numerical bracket width and |reported pressure residual| <= 1e-7 Pa, not just a volume residual below the much looser 1e-12 m3 tolerance. At the saved ~1.03 MPa pressure and <=0.001 m3 gas-volume scale, that pressure residual corresponds to about 1e-16 m3 volume residual plus actual rounding. This is an allocation argument on the recorded scale, not a global liquid-derivative proof or permission to assert the future residual. The new actual residual must satisfy the original reconstructed bound.

Representability does not already preclude the proposal: maximum initial-bracket ULP is 1.862645149230957e-9 Pa and saved pressure resolution 1.4348891953413338e-9 Pa, below 1e-7. The saved width 9.004026651382446e-6 Pa halves seven more times to 7.034395821392536e-8 Pa; the old 41 iterations would remain well below 100 if the same stable bisection behavior applies. No number of future HEOS evaluations or duration is guaranteed.

For temperature, the unchanged inverse gate implementation accepts only if (|U_residual|+U_error)/Cmin is within its returned eT. A 1e-6 J energy stop implies eT <= about 3.13925e-9 K at the saved Cmin, or about 1.00798e-5 Pa per endpoint at the saved slope. Together, allocating <=2e-5 Pa actual-fluid and approximately 1.01e-5 Pa temperature per endpoint leaves nearly 4e-5 Pa for both report-to-root terms, root difference, and changed supports. The saved retained representation/declared-error floors are much smaller; reducing those declared errors is unnecessary for this allocation. Every newly obtained support, derivative-domain condition, root sign, actual error decomposition and original gate must nevertheless be recomputed and checked. The current failed record does not become accepted under this argument.

The clock upper distance is 9.255532423371518e-15 s and all original N/U/T comparison gates pass. Selected joint pressure already passes cell 0 (~4.25e-5 Pa) and dry cell 1 (~4.80e-5 Pa). All old independent reported/full-T pressure failures remain saved; joint evidence is the explicit selected strategy rather than relabelling the old gates.

The actual parent consumed 206.958639 seconds, with 32/32 RHS, 4 provider constructions, 3 initial-U returns, and 8 wet requests. Additional inner pressure/temperature work will increase cost. Any later run must retain the same 97 RHS / 16 wet / 510 s aggregate limit and original per-stage budgets; the 570 s supervisor is cleanup protection, not a larger scientific budget. A numerically successful parent may still leave insufficient time for both ordinary branches; that must be retained as resource refusal, not hidden by extending limits.

Evidence: one 2,201,509-byte final raw event was read using the standard library (extract.py: 0.017362 s). Exact saved-field decomposition took 0.002613 s. The full source-study decoder, live reconstruction, source model, EOS, installation and tests were not run. EXTRACT.json retains exact Fractions alongside displays; DIAGNOSIS.json/derive.py retain the computations. This is diagnosis and next-profile allocation, not material validation or a successful dynamic HEOS trajectory.
