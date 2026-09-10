# Independent offline audit: installed native open-column result

**60 independent assertions passed.** Standard-library JSON/Fraction/SHA256 only; no EOS, trajectory, wrapper evaluation or repository modifications. Root's reported 25 assertions were not used as proof.

Saved input: `/private/tmp/brick-programmed-source-column-v1/installed-native-one-step.json`

SHA256: `5932a0d6ce26bb023257025750eaeff9f62ea687496d300e8be994e6f18590f3`.

The result reports completed, reason null, 3 attempted/completed evaluations and 22.20617241700529 s. Its accepted prefix has initial/final three-cell states at exact times 0 and 1/1024 s, one ledger, one complete endpoint observation and a three-cell midpoint snapshot. Fixed dry masses and energy-model identities are unchanged; endpoint inverse energy targets match accepted states; disabled chemical rates are zero; material qualification remains false.

The accepted boundary query occurs at exact t=1/2048 s. Independently interpolating the saved programme endpoints gives gas T=343 K, radiation T=352.5 K, p=1,100,000 Pa, and O2/N2/H2O mole fractions 0.1875/0.71875/0.09375. All match the saved midpoint BoundaryState exactly. Its identity is virtual_design_choice.

Every cell's U, liquid water, and all three gases were recomputed from old state, left/right shared face integrals, local phase integral and accepted signed roundoff using exact Fractions. Every equality passes, including the middle cell's simultaneous left/right contributions. Left external face is closed; right boundary has nonzero gas and thermal exchange. Each face energy decomposition matches its recorded signed decomposition correction.

| Quantity | Saved body change | External contribution into body | Accepted signed roundoff | Exact balance remainder |
|---|---:|---:|---:|---:|
| U (J) | +0.08941944529942703 | +0.08941944530653400 | -7.106981669835477e-12 | 0 |
| O2 (mol) | -7.5388483768423775e-6 | -7.5388483768547484e-6 | +1.2370916194649056e-17 | 0 |
| N2 (mol) | -9.914417825301891e-6 | -9.914417825316421e-6 | +1.4530003177200268e-17 | 0 |
| liquid+vapor water (mol) | -4.459513256293429e-7 | -4.4595132557768063e-7 | -5.166228645849349e-17 | 0 |

The displayed numbers are rounded; exact rationals are in NATIVE_SAVED_RESULT.json. Predictor corrections are excluded from accepted physical balances.

Boundary thermal components over the step are convection -0.00023281944855250148 J, radiation +0.0005357946538441052 J, and conduction into the cell +0.0003029752052330566 J. The signed surface balance defect is -5.854710704959742e-14 J, within the 9.819204465384411e-14 J reported integral tolerance. Conduction into the cell is exactly the negative outward conductive-face integral. Only that conductive term joins gas enthalpy in the body energy update; convective/radiative terms explain the surface balance and are not added again. Total outward boundary energy is -0.089419445306534 J. Its sign includes gas enthalpy in the declared reference coordinate and must not be inferred from the direction of gas mole flow alone.

Reproducer `check_native_saved.py`, actual stdout `NATIVE_SAVED.log`, and `NATIVE_SAVED_RESULT.json` preserve the checks, exact quantities and hashes. This is an offline arithmetic/provenance audit of already saved native output, not independent EOS or real-material validation, and not a bound on trajectory time error. No code freeze was changed.
