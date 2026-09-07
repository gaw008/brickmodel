# Independent review: bounded IAPWS water adapter

Scope: `water_properties.py`, its tests, `WATER_ADAPTER.md`, optional dependency in `pyproject.toml`/`uv.lock`. Read current staged/unstaged diff and complete adapter/tests; checked cached official IAPWS text Table 3 and source feasibility/alignment evidence. This review does not qualify raw sludge or mixtures.

## Findings at initial reviewed state

[HIGH] Caloric acceptance permits nonfinite or thermodynamically inconsistent outputs

File: `src/sludge_sandbox/water_properties.py:269` and `:278`.

The EOS enthalpy/entropy comparisons use `abs(value) > tolerance` without first rejecting NaN; NaN therefore passes the claimed independent EOS check. Finite upstream Cp/Cv are multiplied by 1000 without validating the SI results. Independently reproduced at 300 K saturation: returning NaN for EOS `h,s` still produces an accepted pair; replacing upstream liquid `cp=cv=1e308` returns `cp_j_kg_k=cv_j_kg_k=inf`. Replacing liquid `cp=1,cv=2` returns stable-liquid Cp=1000<Cv=2000 J/(kg K), which violates the stable-phase Table 3 relationship. Positive but inconsistent capacities can thus enter later energy inversion/Jacobian code under a verified-state label.

Fix: require finite EOS caloric values, finite converted SI values and finite residuals before comparisons. Independently reconstruct/check Cp/Cv using official Table 3 Helmholtz derivatives with explicit numerical tolerances. Add regressions for these three reproduced cases. These are numerical acceptance probes, not a claim to protect against arbitrary malicious in-process modification.

## Evidence and accepted boundaries

- Actual command `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_water_properties.py -q`: **73 passed in 1.21 s**, before added regression coverage.
- Independent ordinary-state sweep: 22 temperatures evenly spanning 293–500 K, each with sub-saturation vapor, super-saturation liquid and 100 MPa liquid; **66 states accepted**, no failures, Cp>=Cv>0.
- Original wheel hash matches dependency lock; loader verifies fixed archived originals plus installed Python/VERSION bytes and rejects optional ancillary saturation table. No requirement for arbitrary monkeypatch isolation is inferred.
- Common NIST energy offset is used for all water phases, preserving latent enthalpy and pressure work. Native entropy remains explicitly unaligned; fixed IAPWS R difference remains visible and incompatible models are rejected.
- Ideal u uses official Helmholtz derivative, not known-broken upstream u0/a0. Stable-phase TP checks and saturation Gibbs checks are present. No wet-material, mixture EOS or full coupled-solver qualification claimed.
- Numerical tolerance object is frozen and provider does not accept caller-selected tolerance overrides.

Initial reviewed SHA256:

```text
18f5b1ed7b249cfd92c34ded4d0101d99068b197db1af9b40d94a43849dddf36  src/sludge_sandbox/water_properties.py
99578476feb77777eaba510b0e0baaf3173b3ddc5f894b4bf13bfa6f20393988  tests/sandbox/test_water_properties.py
0c3b93d88c93e078130a53b959c7af15e918624c13a53a390a7a7157258312ed  pyproject.toml
37577748fc08f48dae4b6ac917c4f753b594df72d7b0f8a7762d69b2aafd6958  uv.lock
```

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 1 | warn |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: WARNING — resolve the caloric acceptance issue and independently recheck before approving this adapter. No source edits or commits by reviewer.

## Repair verification — supersedes initial warning

Root repaired the caloric gate, preserving earlier tolerances and adding explicit `heat_capacity_absolute_j_kg_k=1e-5`. The new capacity tolerance compares two evaluations of the same IAPWS derivative equations; it is not a physical uncertainty allowance. I read the actual repaired implementation and matched its Cv and Cp expressions against cached official Table 3. Finite SI capacities and EOS h/s now precede all comparisons; expected capacities are independently checked for finiteness and positivity.

Re-executed tests: **78 passed in 0.64 s** using the same targeted command. Independently repeated all five fault probes: NaN EOS h and s now respectively raise `invalid_finite_eos_h_SI`/`invalid_finite_eos_s_SI`; SI overflow raises `invalid_finite_cp_SI`; Cp<Cv and positive incorrect capacities both raise `iapws_heat_capacity_derivative_residual`.

Additional independent derivative check: 22 temperatures evenly spaced over 293–500 K, each at 0.5 times saturation pressure (vapor), 1.1 times saturation pressure (liquid), and 100 MPa (liquid), **66 states**. Central differences with 0.005 K offsets used backend h at fixed pressure for Cp and backend u at fixed density for Cv, rather than restating the adapter formula. All passed a separately declared finite-difference check threshold of 0.002 J/(kg K). Maximum observed absolute deviations were **2.6812094802153297e-6 J/(kg K)** for Cp and **6.549089448526502e-7 J/(kg K)** for Cv. Difference probes just outside endpoint temperatures check the underlying EOS derivatives only; no adapter domain extension is inferred.

Final reviewed SHA256:

```text
3067908b66d181cb550b40ca8604243505eaab29cb6cb317eeaa7161e8a1a140  src/sludge_sandbox/water_properties.py
1be419238e8f54a36d59d5ac01df2bfb57229bbc3d108287b306bd6768ed6332  tests/sandbox/test_water_properties.py
0c3b93d88c93e078130a53b959c7af15e918624c13a53a390a7a7157258312ed  pyproject.toml
37577748fc08f48dae4b6ac917c4f753b594df72d7b0f8a7762d69b2aafd6958  uv.lock
```

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass; initial finding resolved |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE for the documented bounded pure-water adapter. This approval does not establish raw-sludge parameters, mixture compatibility, wet-brick integration, or independent material validation. Reviewer changed only this report and made no commit.
