# Independent review: default Python water call seam

**APPROVE the isolated default-only refactor.** No actionable CRITICAL/HIGH/MEDIUM finding. This is not HEOS admission, performance evidence or permission to substitute an arbitrary backend. Reviewed 2026-09-07; no EOS or tests were run by this reviewer while Root's water regression session was active.

## Verified diff and compatibility

Reviewed `_water_python_backend.py` and the entire water_properties diff against baseline_water_properties.py. The baseline is byte-identical to current production water_properties.py. Independent AST normalization replaced the nine new dispatcher invocations with their original native calls/accesses and removed the new import; the **entire resulting module AST matches the baseline exactly**. This establishes no unrelated arithmetic, branch, validation, exception-handler, data-field or cache-key edit was hidden in the diff.

The new class contains five stateless static forwarding functions. It neither stores native objects/factories nor converts inputs/results. solve obtains the current backend.IAPWS95 at each call; solver_identity returns that same current attribute. Model calls obtain current `_Helmholtz`, `_phir` and `_phi0` dynamically. Thus existing factory replacement/deletion and model-method fault injection remain visible. The constructor still receives a real native IAPWS95 model, and `_backend`/`_model` fields are unchanged.

There is no public backend-selection parameter, stored dispatcher instance or user-supplied adapter field. Consumers keep the exact WaterProperties type. The direct private consumers remain compatible: chemical standard entropy still calls the native `_model._phi0`, and JoinedWaterVapor still inspects native Fi0 for its positive-Cv proof. The fixed helper is ordinary mutable Python class state, not a security boundary; monkeypatching it is not an admitted alternate-provider API.

Warnings and native exceptions pass through untouched. Existing surrounding catch scopes still perform warning/status/temperature, pressure/caloric identity, stability, Cp/Cv, Gibbs and derivative checks. The callable stack gains one frame, so traceback locations and warning call stacks can change; error classes/messages produced by the unchanged validation logic do not intentionally change. Missing IAPWS95 lookup remains inside the same AttributeError normalization in saturation lookup and the same failure scope in solve.

Reference construction, arithmetic ordering, native units, source-asset hashes, numerical limits, public result dataclasses, method IDs and same-reference object relationships are unchanged. Saturation identity still keys on temperature/reference/assets/limits plus actual backend and current native solver; cache snapshots and validation-on-hit are unchanged. No newly added field enters equality or the special WaterProperties canonical representation, so this refactor does not deliberately alter conserved-state/target tags or reaction/cross-cell identities.

## Bounds and follow-up evidence

This is a call seam for the original source-verified Python implementation only. It provides no computational acceleration by itself and adds a Python call frame; no timing claim was tested. Source verification still establishes the original IAPWS native assets, while the new helper is part of project implementation source and must be included in packaged/source revision evidence. The five scientific source assets should not be relabelled as proof of an unimplemented HEOS backend.

Before any selectable alternate is introduced, the descriptor and consumer binding work documented in `/private/tmp/brick-water-seam-consumer-audit.md` remains necessary: canonical tags, cross-cell/provider/chemical matching, cache identity and emitted transport provenance currently distinguish scientific reference/assets, not alternate execution engines. This approval must not be extended to a future adapter injection path without those gates.

Root owns actual water/cache/response execution. This report does not claim a passing test result merely from the existence of water-tests.xml; source/default golden identity and complete test status should be bound after that session terminates.

## Frozen hashes

- `baseline_water_properties.py`: `ed7adfdd5ca538ab627219948802ba958d84c8afb4def924d47a30898e4625e0`
- `sludge_sandbox/water_properties.py`: `66ccc35c96dae2f54455239a66bd2ccd3a77b183dbdac5d436eff1ab2cd9acd8`
- `sludge_sandbox/_water_python_backend.py`: `f5bad219d665b18ba9b307110a02054590a24866a5d60314944c66b3bbd28171`

Only this review file was written. Production source and candidate implementation were not changed by the reviewer.

## Completed regression and golden evidence follow-up

Read the now-completed XML and saved golden artifacts without rerunning anything. water-tests.xml records **117 cases, 0 failures/errors/skips, 1.075 s**; consumer-tests.xml records **95 cases, 0 failures/errors/skips, .604 s**. These agree with Root's rounded terminal reports of 1.08/.61 s. The earlier pending-execution paragraph is historical and is superseded by these observed XML results.

Reviewed golden.py and independently compared the retained output bytes: baseline.json and candidate.json are identical, SHA-256 `082c0b4069b7c9c41bffeba6cb1ce3cffaa16a06a1da1fbeedf492490f58db61`. There are 30 numerical records across 293, 300, 373.15, 450 and 500 K: one saturation pair, liquid/vapor state and response records, and ideal-vapor output per temperature; four additional records compare domain exception class/message. The script checks saturation liquid/vapor and TP state reference `is` relationships and canonical equality before/after the calls warm cache. It records native reference/assets explicitly and disallows nonfinite JSON.

Root reports separate processes with original and candidate PYTHONPATH, avoiding same-module-name import contamination. The JSON itself does not embed loaded-module paths/hashes or launch metadata, so the process-selection provenance relies on that execution record and the retained source trees; byte comparison alone cannot independently prove interpreter import selection. This is a local unchanged-default regression, not an independent physical oracle. Coverage samples two saturation-relative pressures per temperature, does not cover every pressure/domain boundary or certify interval error, and does not instantiate a full host target to compare its tag. The unchanged canonical/source AST and existing fault/consumer tests provide complementary evidence; arbitrary future dispatch is still outside approval.

Additional bindings:

- golden.py: `362bc5f865633e9a65816e304767e5730f02047700371b8e0ff2d094824ed6a3`
- water-tests.xml: `dc59e48e54653f34f8b6624177ec19c455954b2c691da0834b18ab134aca6b16`
- consumer-tests.xml: `67624a88cdb741a22c5b382b3455c70175a1b7295aea8e176ee0c0c23387e5cf`

Final verdict remains **APPROVE default-Python seam only**, with no unresolved actionable finding. No HEOS, speedup or whole-host physical validation is claimed.

## Correction: original golden import-path binding invalid

Root identified a concrete import-selection flaw after the initial review: directly executing golden.py from the candidate package parent puts that directory at sys.path[0], ahead of PYTHONPATH. Both original launches could therefore select the candidate implementation. The original identical JSON files must be treated as **initial-unbound evidence, not demonstrated baseline-versus-candidate parity**. The prior paragraph's noted missing import provenance is material, not merely a documentation limitation. Its byte-equality observation remains true, but cannot support old/new equivalence.

The independently normalized source AST and actual reported XML tests are separate evidence and remain valid within their scopes. Default-only code approval does not depend on treating the unbound JSON as a baseline run. A replacement golden with separate baseline package, stdin execution, explicit paths and actual loaded-file/hash assertions is pending. No replacement computation was run by this reviewer.

## Final correction verified: separately bound old/new golden

Reviewed bound_golden.py and all retained bound artifacts, with no new EOS execution. The replacement uses stdin (`python -`), cwd `/private/tmp`, separate explicit PYTHONPATH values and a distinct baseline-package tree. Each child asserts its actual resolved water_properties.__file__ before any golden EOS work and emits its source hash to stderr. Precisely: the **path** is asserted before EOS; the hash is recorded there and the parent asserts the two hashes differ after completion. This reviewer additionally checked each recorded hash against the exact reviewed old/new snapshot. It should not be described as a pre-EOS expected-hash assertion that the script does not contain.

The old import resolves to `/private/tmp/brick-water-python-seam/baseline-package/sludge_sandbox/water_properties.py`, hash ed7adfdd5ca538ab627219948802ba958d84c8afb4def924d47a30898e4625e0, exactly matching the frozen baseline. The new import resolves to repository src/sludge_sandbox/water_properties.py, hash 66ccc35c96dae2f54455239a66bd2ccd3a77b183dbdac5d436eff1ab2cd9acd8, exactly matching the reviewed candidate. Current new helper hash also matches f5bad219d665b18ba9b307110a02054590a24866a5d60314944c66b3bbd28171.

Both bound outputs contain 30 numerical cases plus four domain-error records and are byte-identical, SHA-256 082c0b4069b7c9c41bffeba6cb1ce3cffaa16a06a1da1fbeedf492490f58db61. stderr metadata matches bound-result.json. The parent enforces 15 s per subprocess and requires each exit 0; Root reports the complete replacement finished in .85 s. Thus **sampled baseline/candidate parity is now supported by the bound run**, independently of the initial unbound files. Those earlier files remain preserved but contribute no old/new parity evidence.

Bindings: bound_golden.py 211c2a73a5c712cef17c495e6c3229a30e5df540c70a352f81b262e5e9573618; bound-result.json dbda80e1d7db32a82e85ed1c5a0d0f502da9d352dcea5da45a074a404937aeb5; bound-old.stderr 3a69ca91b2484e9dd361c1cc8d9bc623520a544f7258dea4b15f5443a9306ab6; bound-new.stderr 27c2ce5928ad527d372b5044d9f2a94ea670345297c1947d6101f85d56ef8ed8.

Final conclusion: **APPROVE default Python call seam with corrected bound regression evidence.** All prior scope limits remain: no selectable HEOS backend, accelerated-runtime claim, full-domain numerical certification or whole-host scientific validation. The separately reported installed 212-test/38-module result was not independently inspected in this follow-up and is not silently added to the audited counts above.
