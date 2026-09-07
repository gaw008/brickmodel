# Independent review: bounded water saturation cache

Scope: the current diff in `water_properties.py`, `test_water_cache.py`, `WATER_CACHE.md`, the prior cache design and surrounding water validation. This changes computation reuse only; no source, domain or numerical acceptance threshold is re-admitted here.

## Reproduced finding and correction

The initial cache implementation read `self._backend.IAPWS95` outside the existing solver exception boundary. After warming the cache and deleting that callable, an independent probe raised raw `AttributeError`; the previous `_solve` path would have returned `WaterNumericalError('iapws_solver_failed')`. This was a real failure-category regression introduced by the optimization. The implementer added a failing regression and wrapped the new identity read. The reviewer independently repeated the probe against the final source and observed the original numerical error. No unresolved finding remains.

## Cache and physical-contract audit

- The per-provider cache holds exactly one immutable raw numeric snapshot. Its field is excluded from equality, hashing and representation. It retains no mutable upstream phase object and introduces no global cache or temperature quantization.
- The key checks exact normalized T, reference object identity, current source mapping values, numerical-limit values, backend object and actual solver callable identity. Keeping the callable object rather than only its integer ID avoids ID reuse. Changed temperature, source/reference/policy or backend solver cannot silently reuse the old key.
- Cache insertion occurs only after the existing successful solver/status/temperature/quality checks and both complete `_state` validations, density ordering and Gibbs residual. Failed misses are not cached as success. An entry is installed through one complete immutable-object replacement, so concurrent misses may duplicate work but do not expose a partly populated entry. This does not create a global thread-safety guarantee for the upstream warning machinery.
- Hits skip only the nonlinear saturation solve. Both `_state` calls still use the current EOS, derivative functions and numerical limits, followed by density ordering and Gibbs checks. Warm-cache `_Helmholtz`, `_phir` and `_phi0` fault injection remains detectable. Returned state/reference identity is rebuilt for the current provider rather than borrowed from another instance.
- Entry matching is an identity/reuse check, not repeated certification of all files or arbitrary in-process modifications. Construction still performs the original source verification. The cache does not claim general protection against correlated malicious mutations of the upstream model object graph.

## Independent execution

The initial cache-only suite passed **17 tests in 0.39 s** before the missing-callable correction. Final independent execution used:

```sh
PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_water_cache.py tests/sandbox/test_water_properties.py tests/sandbox/test_water_response.py tests/sandbox/test_ideal_water_vapor.py tests/sandbox/test_water_chemical_potential.py -q
```

Result: **181 passed in 1.36 s** (18 cache, 78 original water, 21 response, 28 bridge and 36 chemical). Checks cover exact neighboring float temperatures/capacity, instance isolation, immutable snapshots, warm solver failure/warning/missing callable, current EOS faults, policy/reference/source changes, failed-miss retry and original input-domain gates. The existing count check confirms one saturation solve but four `_Helmholtz` validations across two equal-temperature calls.

A separate reviewer probe queried liquid water at 300 K, first 100000 Pa and then 200000 Pa. Instrumenting the actual backend recorded one saturation solve and two distinct pressure-state solves; the returned densities differed. Thus the optimization did not replace TP pressure dependence with the cached saturation density. The same probe subsequently removed the warmed backend callable and verified the corrected numerical-error category.

`git diff --check` passed. Heavy closed-storage profiling and full installed-project regression are separate parent-run checks; this report does not infer a speedup percentage or assert those results in advance.

## Final SHA-256 binding

| File | SHA-256 |
|---|---|
| `src/sludge_sandbox/water_properties.py` | `ed7adfdd5ca538ab627219948802ba958d84c8afb4def924d47a30898e4625e0` |
| `tests/sandbox/test_water_cache.py` | `022d0f2d20bd16f932b84c5f9492721d5d3ddac2321fa7db804ffd0a3acb669a` |
| `docs/sandbox/WATER_CACHE.md` | `bc491e7b080d6a843c284d90ad43b8584fd3ab4d295803caf1bccfe485034892` |

## Separate read-only solid design review

The reviewer also inspected `SOLID_COUPLING_DESIGN.md`; no solid code was commissioned or reviewed. The proposed constant-molar-volume approximation correctly defines `u=h0-P0*v` and `h=h0+(P-P0)*v`, with Cp=Cv only under that rigid, nonexpanding approximation. Bulk minus explicit solid volume feeds the current fluid cavity, total solid/fluid U requires a new complete inverse, and uncertain solid volume must enter the pressure budget even in the no-liquid branch. Explicit inventory layout and host adaptation avoid treating solid columns as gases or mislabelling a fluid-only error budget as the whole system.

One requested clarification is that the proposed solid **u** error contract must include the uncertainty/rounding in `P0*v`, not merely relabel an h0 error. The implementation-stage provider must also preserve phase transitions and actual source-domain gaps. These are design constraints, not implemented or experimentally validated solid physics. No blocking algebraic issue was found in the inspected design.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass; failure-category finding resolved |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — the bounded saturation-solve cache preserves the inspected source and physical-validation contracts. Solid coupling remains a separate unimplemented design.
