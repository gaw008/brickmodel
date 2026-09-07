# Default Python IAPWS-95 call seam

Scope: extract native backend calls, preserving the already verified Python 1.5.5 implementation. This is preparatory work for a separately verified accelerated implementation. No alternative backend or speedup is admitted here.

The fixed private `PythonIAPWS95Calls` class performs only native-unit dispatch. WaterProperties retains source checks, actual `_backend` and `_model`, conversion arithmetic, error handling, reference, numerical gates, saturation snapshots and validation. Every call obtains the current native method/factory; no captured constructor bypasses mutation/fault tests. No configurable dispatch field is added. Direct consumer access to native `_model._phi0`/`Fi0` is retained. Future alternative admission still requires explicit scientific identity through all consumers; this seam is not that admission.

Evidence:
- Frozen original water_properties.py is baseline_water_properties.py (pre-change HEAD 1ad6a62).
- Isolated existing water properties/cache/response tests: 117 passed, 1.08 seconds, water-tests.xml.
- Isolated ideal-vapor/joined-vapor/chemical-potential consumer tests: 95 passed, 0.61 seconds, consumer-tests.xml.
- Initial direct execution of golden.py did not bind imported module paths and let the script directory shadow PYTHONPATH. Its baseline.json/candidate.json are retained but are NOT evidence of old/new parity. Corrected bound_golden.py executes stdin in separate original and current processes, asserting the actual loaded module path before evaluation and recording distinct old/new source SHA-256 values in stderr. bound-old.json and bound-new.json compare exactly for 30 numerical outputs across 293, 300, 373.15, 450 and 500 K (saturation, liquid/vapor TP and response, ideal), four domain errors, source assets/reference and canonical provider identity. Returned reference object identity and canonical invariance after cache warming are asserted. Both actual JSON outputs are retained.
- These are unchanged-default regression checks, not an independent physics validation or whole-host equivalence proof. Existing official/fault test assertions and thresholds were not modified. No added wet trajectory or full suite was run in the isolated stage.

Reproduce golden from the archived script with PYTHONPATH pointing to a package tree containing the original module, then to the current source tree; compare complete JSON bytes. Archive module classes preserve their original sludge_sandbox module names by separate processes.

Applied package evidence: frozen offline non-editable install; from /private/tmp with no PYTHONPATH, 212 related tests passed in 1.46 seconds. installed-identity.json records 38 actually imported site-packages modules matching current source bytes. This is a targeted installed suite; the earlier full 1112-test result applies to the prior source version only.
