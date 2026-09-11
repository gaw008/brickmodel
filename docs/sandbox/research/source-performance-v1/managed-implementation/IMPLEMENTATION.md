# Managed RHS verification implementation

Four owned files are frozen in FREEZE.json. `test_heos_rhs_scope.py`: 36 passed in 0.20 s, actual final05.xml/log. No EOS call, provider/AbstractState construction, installation or native run. Fake module/native-body tests deliberately bypass only the outer worker admission/physical graph; structural projections are explicitly not physical observations. Normal Python admission is separately rejected.

Private worker API:

```
lease = _admit_worker(adapter, supervisor_pid=os.getppid(),
                      deadline_monotonic=original_begin + original_budget)
try:
    evaluation = adapter.evaluate(state, exact_time)
finally:
    _close_worker(lease)
audit = _worker_audit(lease)
```

Admission is callable only from the actual same-package `source_managed_worker` module executed with isolated `-I -m`, on the synchronous main thread with the actual supervisor PID and a finite future deadline. Root owns that worker's bounded data-only input, fresh constructors, no external callbacks, and process lifecycle. These checks do not attest against malicious native code or direct setter access already inside the worker. They cannot be replaced by a decoded JSON field or a generic user `with` statement.

The lease itself performs no native calls. Each real ExactSourceColumn.evaluate opens an internal scope after rhs_started and exact-time validation; computes the original body; verifies the original live graph plus full per-kernel fluid/config at exit; then publishes rhs_returned. The same storages/chemical objects can be used in valid mode clones. Other adapters, controls or collaborator replacement are refused. Outside an active RHS, including constructors and independent property requests, the original per-point native checks remain.

The closed graph is explicit: ExactSourceColumn/SourceWetColumn; SourceWetStorage, ArlabosseMassCaloric/ArlabosseDryCaloric, ManufacturedFixedFluidVolume, ReactionDisabled and WaterElementConvention; RigidStorage/RigidWaterGas/PressurePolicy/DeclaredNumericalEnvelope; original O2/N2 ShomateGas/ShomateSegment through IdealGasPhase, and H2O IdealWaterVapor; WaterChemicalPotential plus its own vapor; HEOSWaterProperties with original WaterProperties/IAPWS module and actual IAPWS95 instance, WaterReference and NumericalLimits; InversePolicy/WetFace; optional LiquidTransportConfig/SaturationMobilityTable/LiquidConnection. Exact dataclass classes reject instance method overrides before original binding callbacks. Every unique actual HEOS kernel is registered; same digests do not authorize an independently substituted instance. All original `_guard` and operator/source binding checks remain. No generic object walker or new provider protocol is introduced.

Kernel admission binds the exact loaded CP module, native flash/check objects, RLock, reference, original config/fluid/descriptor/identity and scalar constants, plus actual getter functions. Kernel functions outside `_transaction` are AST-identical to the pre-edit version. Its original warning context, phase reset and numerical body remain; only the four global-check guards depend on an active, owner-bound, original-member scope. Within that scope kernel locks are acquired in stable order, every operation checks owner/deadline/member/binding, and wrong-thread/task/PID/nested use is rejected. This managed worker excludes concurrent native clients instead of claiming its lock intercepts raw CP setters.

Audit shape: `{mode, pid, supervisor_pid, closed, rhs, material_qualified:false}`. `rhs` preserves ordered attempts with exact-time repr, native operation count, entry/exit check records (actual observed metadata hashes), status, primary error type/reason, secondary exit error details and actual elapsed. `worker_audit` returns a fresh data-only copy and remains available after close. Exit errors after actual computation preserve the evaluation through existing rhs_failed. Body errors remain the original exception; secondary verification details are retained in the audit and exception notes. All scope state is revoked even on failure. A failed observer runs only outside the closed scope and preserves its original exception and completed candidate.

Evidence sequence: missing module RED preserved; first 11 pure tests passed; second expanded batch had 26 passes and 2 import failures while Root's heos_runtime_registry file was not yet present, retained in second02; after registry availability third03 passed; final05 is the final 36-test run. AST checks in FREEZE prove every nontransaction kernel function unchanged and exact evaluate identical after unwrapping only the new scope. `git diff --check` passed for owned files. ruff/mypy/pylint/black executables were unavailable and none was installed.

Root separately owns unchanged legacy kernel preservation, new reviewed manifest/runtime identities, wrapper/config selection and data-only worker. None is represented as an old implementation with unchanged hashes. Independent reviewer was given final file hashes and the finite test scope before any native execution.
