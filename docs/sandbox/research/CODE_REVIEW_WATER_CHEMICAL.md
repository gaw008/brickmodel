# Independent review: water chemical potential

Scope: `water_chemical_potential.py`, its tests and model documentation, with the existing water reference, ideal-water bridge and multiphase design inspected. No existing water-source gate is relaxed by this review.

## Physical derivation

At the fixed standard pressure 100000 Pa, the native ideal Helmholtz density is `rho=p_standard/(R95_specific*T)`. Its entropy is `M*R95_specific*(tau*phi0_tau-phi0)`. Evaluating the ideal component at this density does not require an actually stable pure-vapor phase at the standard pressure. The resulting standard entropy satisfies `ds0/dT=Cp95/T`.

The bridge preserves native ideal enthalpy with the already established common energy offset. Defining `s_v=s0-R_mix*ln(p_v/p_standard)` gives both `dmu_v/dp=R_mix*T/p` and `dmu_v/dT|p=-s_v`, while liquid entropy remains native and its shifted enthalpy gives `mu_l=h_l-T*s_l`. The shared additive energy offset cancels from the phase chemical-potential difference; it is not a latent-heat source. These references are consistent for this two-water-phase approximation, but do not establish standard entropy compatibility for reactions with other NIST species.

Equilibrium therefore uses the positive exponent `p_eq=p_standard*exp((mu_l-mu_v_standard)/(R_mix*T))`. The implementation back-substitutes chemical potentials and checks a 1e-7 J/mol numerical residual. The native saturation pressure is a comparison from a different vapor EOS, not an identity that may be substituted into this model.

## Independent verification

Before calling the new chemical module, the reviewer calculated five reference points directly using the existing native `_phi0` provider and the formulas above. This is independent of the new assembly, but is **not** an independently expanded implementation of the original Table 1 coefficients. That distinction was sent to the implementer when a test name incorrectly implied the latter.

| T (K) | s0 (J/mol/K) | derived p_eq at native saturation liquid pressure (Pa) | relative difference from native p_sat |
|---|---|---|---|
| 300 | 125.73719510996519 | 3530.8482218640897 | -0.0016847203783738607 |
| 350 | 130.93580655498917 | 41329.66820114837 | -0.008446423386043955 |
| 400 | 135.48372149678266 | 239279.93100786887 | -0.02640449134496592 |
| 450 | 139.54504406348235 | 875680.8989204273 | -0.06063339265486434 |
| 500 | 143.22900616155832 | 2342446.518059965 | -0.11243930656184054 |

The new equilibrium result matched all five precomputed pressures within the preselected 1e-12 relative threshold. These EOS differences are model approximation differences, not numerical roundoff or measured brick errors.

Additional reviewer central differences at fixed pressure used T=300/350/450 K, p=1e5/1e6/1e7 Pa, and dT=0.01 K. For each liquid and ideal vapor, `dmu/dT+s` was below the preselected 1e-6 J/mol/K limit; the maximum observed absolute residual across six cases was 1.25e-8 J/mol/K.

The focused suite was independently run: **36 passed in 0.55 s** at the pre-final snapshot. It covers entropy/caloric and pressure derivatives, unchanged common energy offset, positive subnormal pressure without clipping, native temperature-domain gates, nonfinite source derivatives and immutable/fixed reference pressure. Positive p uses log differences (and log1p near the reference), avoiding underflow of an intermediate p/p_standard ratio. Direct p=0 chemical-potential queries are rejected as nonfinite; the separate transfer layer must represent that physical limit explicitly.

## Final snapshot and verdict

The inaccurate reference-test name has been corrected to `native_phi0_reference`; final model/results explicitly carry a derived method ID and classification. Final independent focused run: **36 passed in 0.55 s**.

Source SHA-256: `fe71a2bdcd7355889d4c15545151eb14c6d83bae5924f5dc5c07e52c2a63d4bd`.

Test SHA-256: `c240bbb169340d6aa071754857bec413e85e4638a321c3e9c339e4e116ba7da8` (final metadata assertions inspected and independently rerun: 36 passed in 0.55 s).

Document SHA-256: `856e473d45c7c334c8aca461d2fd97f3bbdbce0ab49be1795ce5d421aea9f5db`. The untested wrong-source-object coverage claim was removed; actual anomalous-phi0 coverage remains. No numerical or physical implementation defect has been reproduced in the final snapshot.

The reviewer also inspected `water_chemical_oracle.py` and its preregistration without rerunning the existing native-phi0 experiment. Its ideal entropy/enthalpy oracle expands the archived Table 1 coefficients with stable expm1/log arithmetic and the correct derivative signs; the liquid EOS remains shared and explicitly disclosed. Candidate-module calls are only on the comparison side. `Path(__file__).resolve().parents[3]` correctly resolves the repository root. The script binds source facts, reference alignment, implementation, script and preregistration hashes, requires finite JSON and exits unsuccessfully on failed registered thresholds. Its default output is replaced on rerun, so the parent is retaining the first artifact separately before final binding. This limited code review does not claim an independent liquid EOS or new material-validation evidence.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — the reviewed physical scope remains derived pure-liquid/ideal-water equilibrium, not sludge activity or nonideal mixture admission.
