# Saved/live source-asset mapping interoperability fix

APPROVE for source SHA-256 `5695976e4f655bca189c7eadd87e62a321c048349d1ddcbf79a74b12f2d52e36` and test SHA-256 `0f5d3636f532ba0c8e2df1eb68cc47b16923e5246e3748ef538ac9811d85821b`. The runner remains `ec89719e1cdee5709d0baa571601b7951577b3be39d4dc5655e0e44c623be094`.

Read the actual first installed-run JSON and traceback: it stopped at `source_pressure_model_binding` after two completed backend/reference-anchor constructions, zero new endpoint evaluations and 1.0984587920247577 s. The source model identity and underlying assets matched, but the passive decoder returns a dict whereas the live HEOS wrapper exposes a MappingProxyType. The prior `_same` rejected the different container types before comparing their contents. This was an interoperability false rejection, not an exceeded scientific tolerance.

The correction is restricted to `source_asset_sha256`: both sides must be Mappings with exact built-in string keys, then their ordinary dict views are compared using `_same`. Exact key/value content and value types are retained, including rejection of string-subclass aliases. Other identities, policies, liquid-pressure binding, metadata restrictions, error arithmetic and qualification fields are unchanged. The existing decoder and real storage constructor are unchanged.

Eight independent executable tests passed in 0.47 s (`mapping-review.log`, `mapping-review.xml`). Using a manufactured liquid seam with the actual source-storage interface, equal dict and MappingProxyType inputs yield identical initial bounds and continuation. Changed values, missing/extra keys, key/value type aliases and non-Mapping inputs all fail. The tests performed no native EOS computation. The three unchanged helpers and earlier unrelated tests were not rerun.

After the parent's affected tests and installed-byte identity checks pass, repeating the original runner once with the same pinned inputs, 20/30 s budgets and unchanged numerical conditions is justified by this identified correction. The first failed JSON/log must remain preserved. No outcome for that subsequent run is claimed here.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — narrow mapping representation fix, preserving exact source contents and all numerical gates.
