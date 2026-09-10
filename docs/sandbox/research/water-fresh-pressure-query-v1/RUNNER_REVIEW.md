# Fresh query runner review

Reviewed build_query.py bee6cefe5f310ea92a1756b44018d824e63db5018cc97a744a8be02f7b473fee; propose_boxes.py 5b8ab42f7bc75798d69a571032a24833a9ba0228486cf10e081949a06fba1e35; run.py ae2ae74ab59176928a11550db9e4b53e2312e36ab14353800c9027041a9ea4d8. Read actual WetPair/WetCellRate/WetMixedInverse and consumer candidate contracts. No native execution, provider construction, installation or repository edits.

No CRITICAL/HIGH issue found in this bounded candidate. This is code approval conditional on root completing the actual installed freeze and external supervisor; it is not authorization to run an unfilled/missing execution manifest. Current HELPER_FREEZE covers old builder and original source inputs but does not replace the future complete execution freeze.

Actual flow produces two initial energy-setting forward points at new temperatures 300.125/305.25 K, followed by one fresh two-cell pair.evaluate. It does not import saved successful outputs. The misleading old builder attempted-point parameter snapshot is explicitly distinguished from the newly saved actual case. rates.cells[0] matches WetRates.cells and BoundLiquidPressureRequest.capture signature. New state inventories/energy and original numerical policies remain explicit. Full source descriptor/pair identities are retained by request capture; old helper code reuse does not admit the old runtime.

Seed proposals use the actual nominal temperature and original source ANCILLARIES, then at most12 mathematical point Newton iterations. Approximate seed calculations confer no certificate. Every candidate box must pass the consumer's independent full-parameter proofs. The nominal precision60, stop1e-30, coex widths4e-6/.001 and mechanical/query radius.2 only select numerical boxes; they do not alter inverse epsilon, material/error declarations, or actual model-domain gates. parameters(request,policy,60) obtains original query inputs; no pressure/temperature error is silently reduced in the runner.

Budget logic is cumulative whole60s, native construction/query30s including initial work, and proof min(20s,remaining whole budget) with4 operation attempts and256 boxes per primitive. Seeds have12 iterations plus the whole deadline. These cooperative guards cannot interrupt a single native call; the external watchdog and process reaping are essential and remain to be prepared. The script correctly does not claim native-internal residual-call counts.

Pressure evidence dataclass field names match consumer. The general data encoder handles actual evidence's dataclasses/Decimal/Fraction/bytes and refuses unknown objects. Failure summary captures exceptions/traceback; evidence is saved before post-proof guard. Native/seed failure partial files are preserved. Freeze reading happens before try; malformed/missing execution configuration is a launcher/preflight failure rather than a saved scientific result, so the external supervisor must preserve its process outcome.

Independent pure tests: review_pure.py, review-pure02.log:3 passed in0.004s. Actual proposal control flow with explicitly analytic mock residual/J tests untrusted status/counts and failure-before-evaluation; actual unresolved LiquidPressureEvidence serialization tested. No EOS math or native flash was run. First reviewer harness attempt used unsupported SimpleNamespace as a saved mock result and failed1/3; retained review-pure01.log and pre-fix reviewer script. Fixed only the reviewer fixture to a dataclass, matching the actual result class contract. This does not assert native-positive execution.

Pre-run requirements already communicated to root: fill execution freeze with all three current scripts, installed modules/dependencies, old helper and all transitively read inputs, coefficient JSON/PDF; freeze explicit membership for installed module and water-source trees. Save/check memberships again at final exit, not merely listed file hashes. Current guard checks installed membership; finalizer hashes existing frozen paths only. At present no external supervisor is in reviewed scope.

[LOW] Seed source file opened without deterministic closure
File: propose_boxes.py:21
Issue: json.loads(open(...).read()) emits ResourceWarning in the pure test.
Fix: use Path(...).read_text() or a context manager. One bounded read is not a numerical blocker, but clean resource handling is straightforward.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 1 | note |

Verdict: APPROVE bounded runner code with the stated pre-run freeze/supervisor prerequisites; no native/result approval claimed.

Final narrow readback: run.py 59ba8d8bf70d98a76b48bc738a3f01a9aa0ea760e12c25fee08136c01c881b59 adds asset-directory membership guards and final installed+asset membership capture with failed status on mismatch. This closes the membership recommendation without changing scientific work or limits. Execution freeze/external supervisor still pending at review. Other reviewed source hashes unchanged.

Execution preflight closure: independently rehashed EXECUTION_FREEZE b810a64c47c789532e6b9dc131cfab7c9b8f82c1e3db5711f98517d0d5c8f92f and all247 listed files; zero mismatch. Current installed101-module membership and all declared asset-directory memberships match exactly; every asset member is hashed. direct_url has no editable flag. All four runner/helper/supervisor files are frozen. Evidence saved review-execution-freeze.json. Proposer a177f39f51daae390387a74ce46e172c966ba0cd36c0b3872c3d858a165788b6 resolves the LOW file closure finding with Path.read_text; numerical code unchanged.

Supervisor 0ff1e1dbeb59975d7a43a6fe047f6b372d75746361e4478edf2b34c9eae47cc2 launches one subprocess in a new session, waits70s, SIGKILLs its process group on timeout, then waits for reaping and writes exclusive outcome/log files. Runner hash checked before launch and reported after. Whole/query/proof limits remain60/30/20; supervisor outcome remains authoritative if process cannot emit a final summary. Use the frozen venv interpreter from the research directory without PYTHONPATH/overlay (supervisor inherits its executable/environment).

Final disposition: APPROVE one preregistered bounded actual invocation after the already-running installed regression finishes successfully. No unresolved code finding; no native execution or result success claimed by this review. Original material/error conditional qualification remains mandatory.
