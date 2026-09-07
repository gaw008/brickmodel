# Independent review of isolated water-backend feasibility evidence

Reviewed 2026-09-07. Verdict: **WARNING — accept the recorded two-point feasibility evidence with the two runner limitations below. No production-backend approval.** No CRITICAL or HIGH issue identified in this narrowly scoped disposable probe; two MEDIUM operational issues. The author report's zero-MEDIUM summary should not be read as this independent verdict.

## Scope and method

Read probe.py, REPORT.md, result.json, run.log, profile.txt, all three manifests, install and initial-failure logs, installed metadata/license, extracted fluid JSON, and the relevant current WaterProperties and installed iapws source. Ran `git diff -- '*.py'` (empty), read-only Python standard-library JSON/arithmetic/SHA-256/AST checks, and executable availability checks. Ruff, mypy, pylint and black were unavailable on PATH and in the probe/project venv bin directories; no installation was attempted. No EOS library was imported, no probe/benchmark/simulation was executed, and no environment, production code, existing evidence or manifests were changed. This new review file is the sole write and is intentionally outside the author's original manifest.

Public web citations in REPORT.md were not independently fetched; source and license verification here concerns the actual locally installed/cache assets, not a release reproducibility or legal audit. Prior workspace memory was not used as evidence for any result.

## Findings

[MEDIUM] SIGALRM is a cooperative timeout, not a hard native-call deadline
File: probe.py:2-3
Issue: The Python handler raises TimeoutError at the next opportunity to run a Python signal handler. A long-running native call need not return control by 30 seconds. Thus this mechanism cannot establish a hard wall-clock cap for an EOS extension. The current recorded run completed normally in 1.0365274579962716 seconds; this limitation does not invalidate it.
Fix: Before reusing as a bounded runner, supervise the process from a separate process with a wall-clock deadline and termination escalation. Describe the existing alarm as cooperative. No timeout/fault-injection experiment was run in this review.

[MEDIUM] Failed reruns can leave stale or partially replaced success artifacts
File: probe.py:16,37,40-41
Issue: The fluid dump, profile and final result are written directly into reused fixed filenames at different stages. An exception before the final write leaves a previous result.json intact; interruption during write can truncate it. There is no run identity/status record binding the artifacts to success. Exceptions are not swallowed and normally give a nonzero process exit, but consumers must check that exit and the per-run manifest rather than assume file existence means success. No evidence of stale contamination was found in the supplied successful bundle.
Fix: For subsequent runs, use a unique run directory and explicit success/failure metadata; publish completed results atomically after success and retain failure logs separately. Do not change the frozen evidence retrospectively.

## Verified numerical and source evidence

- All 19 independently checked hash/size records passed: 11 artifact-manifest entries, 2 result.json source hashes, 5 installed asset records and the installed license record. Current production water_properties.py matches its recorded SHA-256. Parsed run.log equals result.json exactly. Hash agreement establishes internal/current-file consistency, not independent execution attestation.
- Both points are 300 K with pressures 304469.31354 and 567435.65536 Pa. IAPWS receives pressure divided by 1e6 (MPa); native mass-specific h/u/s/cp/cv are multiplied by 1000 to SI. CoolProp receives SI pressure and returns SI properties. The old response's alpha/kappa/molar derivatives are correctly distinguished from the raw IAPWS caloric values.
- Every stored absolute/relative difference and timing mean was recomputed exactly from JSON. Both backend dv/dT = (M/rho) alpha and dv/dP = -(M/rho) kappa agree with stored values; du/dP = -T dv/dT - P dv/dP agrees to arithmetic tolerance. CoolProp's directly queried molar derivative is the appropriate fixed-T quantity. No finite-difference or interval certification is implied.
- The stored CoolProp h-u-P/rho residuals recompute exactly: 9.818086255108938e-8 and 1.08211679616943e-8 J/kg. They are evidence to preserve, not an independently certified numerical error budget. The rounded maximum differences and saturation pressures in REPORT.md are consistent with result.json.
- Both saved phase flags say liquid; cp/cv/kappa are positive, and both pressures exceed both recorded saturation pressures. This is a consistency check of saved results, not a fresh phase solve.
- Native molar R values are exactly equal at 8.314371357587 J/mol/K. The mass values differ by exactly one floating-point ULP: 0.018015268 versus 0.018015267999999997 kg/mol. The probe contains no set_reference_state call, and raw h/u/s comparisons bypass the adapter's formation-energy transformation. Local installed IAPWS ideal Helmholtz lead/log/Planck-Einstein coefficients match the extracted CoolProp values examined. This is not an exhaustive coefficient or revision audit.
- WaterProperties builds the separate ideal-vapor formation-energy anchor; its pressure derivative is unaffected by a constant energy offset. A future adapter must preserve this reference and exact admitted constants explicitly rather than infer compatibility solely from two-point agreement.
- Installed CoolProp metadata says version 8.0.0 and MIT; the copied LICENSE is 1103 bytes and identical to the installed license and cached license. Actual cache package root: `/private/tmp/brick-water-backend-probe/uv-cache/archive-v0/_2aQK4D33XlH4O8FOyHN6/`. Its `coolprop-8.0.0.dist-info/METADATA` matches installed metadata, and `coolprop-8.0.0.dist-info/licenses/LICENSE` matches the copied license. Extracted Water EOS records Wagner-JPCRD-2002. This verifies local asset identity and notice retention, not the original downloaded wheel hash, complete upstream source provenance or optional-backend licenses.

## Timing interpretation and limits

Recomputed raw ratio is 338.1684768758621; validated-response ratio is 446.31526004194575. All loops alternate the same two pressures at fixed 300 K, use the same interpreter/environment, and exclude imports and initial construction. The IAPWS side constructs an object for each call; CoolProp reuses mutable AbstractState and retrieves eight properties. Warm saturation cache is visible in the setup and current source. These are intentionally different work bundles, not equivalent adapter implementations.

There are only 20/20/1000 calls, ordered batches, no independent repeats, uncertainty estimates or randomized ordering. The CoolProp timed bundle omits three molar derivatives and independent source, Helmholtz, Gibbs, response, domain and fault checks performed elsewhere by the validated interface. Dependencies also differ from the project environment. No factor here is a host, inverse solver or production adapter speedup.

The one-call profile agrees with current source: IAPWS95 uses IAPWS97 density initialization then scipy fsolve; saved counts include six density residual evaluations and twelve _phir evaluations. The existing saturation cache skips the nonlinear saturation solve but still validates both phases and Gibbs. Counts and 5 ms duration are one recorded profiled call only.

The initial retained TypeError occurs at the first response call before any timing loop. The corrected source uses keyword-only phase. The original failing source revision is not retained; its traceback is evidence of the failure, not a reproducible source snapshot.

The two liquid points justify considering an isolated adapter experiment only. Broad-domain accuracy, vapor/critical/two-phase behavior, immutable/thread-safe ownership, reference mutation, official verification points, production failure contracts and wet-host inverse gates remain unverified. Production substitution remains unapproved.
