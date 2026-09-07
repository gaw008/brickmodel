# Water backend feasibility — two liquid points only

Verdict: feasible candidate for a separately verified HEOS adapter; **no production replacement approval**. No repository files or error gates changed. All work is isolated under this directory. No full wet trajectory or large-domain scan was run.

## Sources and installation

- [CoolProp Water documentation](https://coolprop.org/fluid_properties/fluids/Water.html), read 2026-09-07: Water HEOS cites Wagner & Pruß (2002), DOI 10.1063/1.1461829, the IAPWS-95 formulation. Its advertised T maximum 2000 K / P maximum 1 GPa do not extend the existing adapter's admitted 293–500 K / 100 MPa domain.
- [Official low-level API](https://coolprop.org/coolprop/LowLevelAPI.html): reusable AbstractState, enumerated inputs, native partial derivatives and automatic phase determination. The probe used HEOS, not IF97, tabulation, REFPROP or imposed-phase shortcuts.
- [Official MIT license](https://raw.githubusercontent.com/CoolProp/CoolProp/master/LICENSE) permits use/distribution subject to retaining the notice. Installed package license is copied locally and hash-bound in license-manifest.json. This review concerns the CoolProp core, not every optional third-party backend.
- [PyPI metadata](https://pypi.org/pypi/CoolProp/json) and actual install.log identify CoolProp 8.0.0. Public wheels were installed using uv into this directory's venv: iapws 1.5.5, numpy 2.5.3, scipy 1.18.1. Downloads reported about 34.8 MiB for the three binary scientific packages, plus iapws; resolution 1.04 s, preparation 10.27 s, installation 44 ms. Installed binary/METADATA/RECORD hashes are in installed-assets.json; this is not a claim that a retained original wheel was hashed.

Initial sandbox attempts failed on default uv cache permissions and restricted DNS; retry used an isolated cache and authorized public network download. No project environment was modified. The first numerical attempt miscalled a keyword-only phase argument; attempt01-failure.log is retained. No timing loop ran in that attempt. The corrected run completed in 1.037 s under a 30-second alarm after the other agent reported its wet smoke finished. Timing is a short single-process observation, not a statistically controlled machine benchmark.

## Model and reference compatibility

The extracted installed fluid definition coolprop-water-fluid.json records Wagner-JPCRD-2002 and the original ideal Helmholtz lead/log/Planck-Einstein coefficients. Its fitted molar R = 8.314371357587 J/mol/K agrees exactly with the existing native IAPWS fitted R. Nominal M = 0.018015268 kg/mol agrees; the existing adapter computes 0.018015267999999997 from division, a one-ULP representation distinction that a replacement must not silently ignore in strict identity gates. Neither uses modern CODATA R = 8.31446261815324 in this liquid EOS.

No set_reference_state call or fitted h/s translation was made. Native h/u/s were compared directly. Existing WaterProperties still has its separate common water formation-energy offset; a future adapter must preserve that explicit convention and its ideal-vapor anchor, not independently zero the liquid or apply the offset twice. Agreement at two points plus matching nominal formulation is not a complete audit of every 2018 IAPWS revision, coefficient or numerical ancillary. The installed fluid JSON contains superancillary/critical-region machinery, which needs separate saturation/domain verification.

## Measured comparison

Both points are T = 300 K, P = 304469.31354 and 567435.65536 Pa. CoolProp independently returned liquid in both cases, with positive cp/cv/compressibility. Saturation pressure at 300 K: CoolProp 3536.8067523441 Pa versus existing 3536.8067522740 Pa. These pressures are safely on the stable liquid side. Full unrounded values/differences are in result.json.

Maximum absolute two-point differences (SI): rho 2.06e-11 kg/m³; native h 4.81e-8 J/kg; native u 5.02e-8 J/kg; native s 8.86e-11 J/kg/K; cp 3.07e-9 J/kg/K; cv 8.08e-10 J/kg/K; alpha 6.54e-16 K⁻¹; kappa 9.60e-23 Pa⁻¹; molar dv/dT 1.18e-20 m³/mol/K; molar dv/dP 1.91e-27 m³/mol/Pa; molar du/dP 4.31e-18 J/mol/Pa. CoolProp's du/dP was queried directly as a thermodynamic partial derivative, while the existing response computes −T dv/dT − P dv/dP. These are local sensitivities, not interval bounds.

Alternating these same pressures at fixed T (imports/constructor excluded):

| Path | Calls | Mean time |
|---|---:|---:|
| iapws.IAPWS95 raw TP object | 20 | 2.988 ms |
| Existing source-verified state_tp_response, warm saturation cache | 20 | 3.944 ms |
| Reused CoolProp HEOS, automatic phase, eight thermodynamic outputs | 1000 | 8.837 µs |

The raw speed ratio is approximately 338; the comparison with validated response is approximately 446. The latter is **not** an adapter speedup: CoolProp timing omits the existing independent source/stability/Helmholtz/Gibbs checks, and its eight outputs are not an entire WaterResponse construction. Dependencies also differ from the project venv. No promise of 338-fold host speedup follows.

Static inspection and the one-call profile.txt agree on cost origin: water_properties.py:288 constructs Python IAPWS95 on every TP query; iapws95.py:619–645 seeds density with IAPWS97 and solves with scipy fsolve, repeatedly evaluating Python residual Helmholtz derivatives. The validated path also recomputes both saturated-phase state validations/Gibbs checks on cache hits, caloric and pressure identities, and local response derivatives. Profile recorded 2050 calls, approximately 5 ms, including six density residual evaluations and twelve full residual-Helmholtz evaluations. These counts describe one measured response, not every inverse.

## Concrete next gate

Build an explicitly opt-in isolated adapter with pinned CoolProp version, binary/fluid-definition/source identity, unchanged native R/M and common energy reference, immutable returned snapshots, per-instance mutable HEOS ownership, and the current phase/domain/numerical failure contract. Retain the existing backend as independent comparison. Before production eligibility, run the original official printed IAPWS verification points, both phases and saturation/Gibbs, independent pressure/caloric/Cp/Cv/response derivative checks, all source/fault-injection/domain regressions, cache/reference-mutation isolation, and the same closed-storage inverse error gates. Any necessary numerical error bound must be established, not copied from two-point differences. Then run the already registered short wet entropy/host comparison under original gates, with explicit source binding. Do not start a 2048-panel wet scan on the basis of raw timing alone.

This is a performance route within the same intended pure-water EOS, not new sludge, sintering or multiphase material evidence.

## Review Summary

| Severity | Count | Status |
|---|---:|---|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | info |
| LOW | 0 | note |

Verdict: APPROVE isolated feasibility evidence only; production substitution remains unreviewed and unapproved.

## Independent review correction (no benchmark rerun)

Root's independent Python review found two MEDIUM weaknesses in the exploratory runner: (1) Python SIGALRM is cooperative with respect to a long-running native call and is not a reliable process-level hard cap; (2) writing result.json in place can leave a previous success behind if a later attempt fails before replacement. The actual successful run measured 1.037 s, within the intended 30 s, but the original text's alarm must not be read as a hard timeout guarantee. Its result belongs only to this recorded successful invocation, not to arbitrary reruns of probe.py.

Original successful probe.py, REPORT.md, result.json, run.log and artifact-manifest.json were preserved byte-for-byte in success-attempt01-snapshot/ before this correction. Future execution must use an external supervisor with subprocess timeout, terminate/kill-and-wait on timeout, an exclusively created attempt directory, and atomic status transitions from running to completed/failed/timeout. Record argv, interpreter/dependency identities and source hashes before and after the child; only a completed status with matching attempt ID and validated output may expose a result. Never fall back to a prior attempt's result. The old exploratory runner has deliberately not been modified or rerun; these requirements apply to its successor.
