# Independent result review — source-matched wet callback 02

Reviewed 2026-09-07. **APPROVE the saved single source-matched nonzero-K callback result and the bounded software-admission evidence it supplies.** No actionable CRITICAL/HIGH/MEDIUM finding in this result audit. No EOS, callback, simulation or integration was rerun by the reviewer. This is not a full wet trajectory, depletion, entropy certificate, scientific external validation or free-sintering approval.

## Actual execution and provenance

The reviewed external supervisor source hash is 939a86f4a8a45a127e49c18009c8fc9f7bd296d79243741bf3f3d2e6fb2f36d1. run/metadata.json selects the isolated candidate package via PYTHONPATH, the repository test helpers and project Python explicitly in an argument vector passed through /usr/bin/env. The exclusive attempt directory is this callback's `run/`; its local attempt_id is `run`, so consumers must retain the full path, not just that basename.

run/status.json records complete, returncode 0, elapsed 1.3871458339999663 seconds under the 30-second requested wait, leader reaped and no cleanup signal errors. result.json says passed and reports 0.847617875013384 seconds inside the child. Parsed run/stdout.log equals result.json; run/stderr.log is empty. The child explicitly exits 1 if its scientific status is not passed. PLAN.json still says prepared_not_executed because it is a frozen preregistration; execution outcome is supplied by the status/result, not by mutating that prior plan.

All **113 declared input file size/before-hash/after-hash triples** match current files. These include the child, plan, prior pore review, candidate modules, test helpers and source assets. The recorded supervisor hash also matches its reviewed current file. This is considerably stronger local binding than the prior callback's fixed files, although before/after hashes are observations rather than immutable filesystem attestation and do not bind every environment binary/dependency automatically.

## Comparison to callback 01

AST comparison confirms every physical setup statement, calculation and assertion in the try body before result serialization is identical to the original `wet_callback_child.py`; all Assert nodes are identical. Changes are the attempt/output identity, addition of saved chemical operands and explicit scientific-failure exit propagation. In the model, the separately reviewed current-pore fix addresses the prior transport-context failure; the original physical fixture is retained.

The fixture is one prescribed cell at t=.5, 300 K initialization, solid 2 mol, vapor water 1e-8 mol, liquid water 1e-4 mol and tracer .001 mol. Normal/tangential stretch is .95, viscosity is 3 Pa s (nonzero dissipation is intended), and K is 1e-7 mol/(s Pa). No accepted time trajectory is constructed. The callback's original inverse policy is **1e-5 J / 1e-4 K / 100 iterations**, verified in saved output and unchanged helper source. It must not be confused with the separate failed fixed-inventory partial experiment's 1e-6 J/1e-6 K policy.

## Independent arithmetic from saved native operands

Using Decimal.from_float at precision 60 on saved liquid mu, standard vapor mu, R and T reproduces `peq = p0*exp((mu_l-mu_v0)/(R*T))` exactly as saved: **3531.5200776812662 Pa**. Both chemical potentials are J/mol, R*T is J/mol and the exponent is dimensionless. The callback's value differs by 9.094947017729282e-13 Pa, below the unchanged 1e-6 Pa gate. This is independent assembly from shared native chemical providers, not an independent water model.

Exact Fraction assembly of `pv=Nv*R*T/Vg` gives the saved 0.2978823868373455 Pa. With K=1e-7, `r=K*(peq-pv)` gives **0.0003531222195294429 mol/s**, versus callback 0.0003531222195294428 mol/s, difference 1.0842021724855044e-19 below the unchanged 1e-13 mol/s gate. Positive rate means this fixture evaporates. The saved species difference is exactly `[0,+r,-r,0]`, and the vapor/liquid pair cancels exactly as Fractions.

The five saved powers are body 0, dissipation 2.24376731301939e-5 W, elastic 0.007289047097178239 W, interface -0.0004274999999999999 W and pore 1.2097869412280353 W. Their sum agrees with 1.2166709259983437 W within 1e-15 W. Child assertions require each component and net power to remain identical to the underlying host, preventing an extra latent-heat source in this callback. Raw underlying arrays are not separately saved; that identity claim is supported by the unchanged successful runtime assertions, whereas the saved sum and exact species cancellation were recomputed offline.

Current area .009025 m2 equals .01*.95**2 and width .0095 m equals .01*.95. One total inverse is recorded and asserted; thermal-inverse identity, matching error bound, current storage identity, tagged total state and current face geometry assertions passed. The recorded inverse temperature bound is 1.853014612597987e-8 K. These establish this callback's wiring and local comparison, not integrated energy or phase-event behavior.

## Qualification-only edit assessment

It is now accurate to remove only `_not_wrapper_admitted` from DeformingSolidHeatEvaluation.qualification, producing `prescribed_fixed_solid_total_energy_not_free_sintering`. The explicit prescribed, fixed-solid, total-energy and not-free-sintering restrictions remain. Removing the stale software-admission denial does not claim unrestricted wrapper correctness, full-domain wet numerics, depletion support or trajectory convergence. Root may make this exact string-only change alongside the four already-reviewed module changes; this review did not edit source. Applied source/test-path relocation remains subject to final diff verification.

The separate failed two-step partial pore-work gate remains FAILED. Callback02 does not overwrite that result or authorize longer wet work. The nonzero callback now supplies the specific evidence absent from the earlier no-EOS admission review, with all wider limits retained.

## Frozen artifact hashes

All paths below are relative to this callback02 directory. The reviewer only adds this report and its companion manifest.

- `PLAN.json`: `0b56400d4854826ec6d63daf0bc2762dd6e04b939a57f37aa0b24f82d4ddf13a`
- `child.py`: `1dc0b5635032e7f7cdd1f6649d386c869d930fed8f2909d34812de914ed039dd`
- `result.json`: `c09e80013518748edac85f9dc688ad2b3af60cb6c6804a4fef92928b5c9b1594`
- `run/metadata.json`: `8130e90d0326e0ddc26235d854e887c68888070becd894bc0ba27d3ca607746f`
- `run/status.json`: `1d1f398ce1784dd353b013e70c3f6614d1757e6b101b8cd19a26d5f5c507fcf8`
- `run/stdout.log`: `26f6ef5233b9d1439bebb8bafa4d80daf0c29b0d6f0f6d4bca2c9f9372a77e61`
- `run/stderr.log`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

## Applied-source and test-path follow-up

**APPROVE the inspected applied diff.** All four repository module contents match the independently reviewed isolated candidates byte-for-byte except the precisely approved qualifier deletion in deforming_solid_heat.py. Its remaining text is prescribed_fixed_solid_total_energy_not_free_sintering. No other source change was introduced by application.

The new tests/sandbox/test_deforming_wet_admission.py differs only in baseline path relocation and reading the live WaterPhaseTransfer module via actual_module.__file__. Every assertion has an identical AST to the reviewed candidate test. Both archived baseline sources match the original retained bytes. The relocated root/path calculations resolve to the repository docs baseline; the live-module lookup checks the actual loaded implementation.

Read, did not rerun, docs/sandbox/research/deforming-wet-admission/applied-tests.xml: **34 passed, 0 failures, 0 errors, 0 skips, suite time 73.000 s**. Cases comprise nine admission tests, eleven storage tests and fourteen host tests. This includes the actual wet deformed-point inverse and original-volume-uncertainty refusal tests, plus test_dry_compression_analytic_and_actual_accepted_components taking 70.666 s. That expensive fine compression test is explicitly dry; it is not a successful full wet trajectory. Root reports its intended exclusion via -k 'not convergence' did not match that test's actual name. The actual executed 34-case evidence is preserved; this reviewer did not repeat it or retrospectively call it a light-only run. Full-suite validation is separate and not yet established by this XML.

Applied bindings (repository-relative):

- `src/sludge_sandbox/deforming_solid_heat.py`: `3c7b42ad5c6a0d155b39cd9e8cce250a93d64865ef57db4a74f57a80230c357e`
- `src/sludge_sandbox/deforming_solid_storage.py`: `8ee7490c1b46616efc404689ce74b40dd62d9d18e23c4966e636702f99592603`
- `src/sludge_sandbox/programmed_solid_fluid_heat.py`: `a2e3136ee3a62d102f1fb5b36816e97942ffd484fa3939ad06d0e300fe19e2da`
- `src/sludge_sandbox/water_phase_transfer.py`: `0463ed85ad4719e65c5c617526dd8520f46f9511426a6f0c69ff95ef0f9c2fb1`
- `tests/sandbox/test_deforming_wet_admission.py`: `16393e199bed1919cedac5c6f0487efd1c74591e1d04439ebb1ef3581bf022a8`
- `docs/sandbox/research/deforming-wet-admission/applied-tests.xml`: `8b8e4e22d3fb63749333a1d87fc59f280c78d738f6fdd7ddd46f2fb796034a12`

Exact applied test command, supplied by Root from execution tool session 18192, cwd repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_deforming_wet_admission.py tests/sandbox/test_deforming_solid_storage.py tests/sandbox/test_deforming_solid_heat.py -q -k 'not convergence' --junitxml=docs/sandbox/research/deforming-wet-admission/applied-tests.xml
```

Root reports terminal exit 0 and 34 passed in 73.00 s. There is no separate raw stdout file; the XML was independently read and agrees. This command provenance is attributed to Root's retained tool session rather than a nonexistent log. Final review frozen after this addition.
