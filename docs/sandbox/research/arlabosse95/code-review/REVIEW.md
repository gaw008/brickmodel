# Arlabosse95 discrete-source module code review

Verdict: **APPROVE the final scoped version**. One MEDIUM Decimal-context defect was independently reproduced and fixed during review; no actionable finding remains above the 80% confidence threshold. This is an internal code review of discrete source lookup and relative chemical-potential evaluation, not independent experimental or whole-material qualification.

## Scope and final versions

Reviewed `src/sludge_sandbox/arlabosse_desorption95.py`, `tests/sandbox/test_arlabosse_desorption95.py`, the four JSON files in `data/sandbox/research/arlabosse95/`, associated extraction/source-review records, and the existing evidence-registry interfaces. Unrelated CLI, HTTP, source-view and asset WIP was excluded and preserved. No source, tests, data, documentation or Git state was modified by this reviewer. Review writes are confined to this directory.

| File | Final SHA256 |
|---|---|
| arlabosse_desorption95.py | `a197a22c095c87f4e388b86c648b7cdcd18cbf75eed34575e10ca09f347137f8` |
| test_arlabosse_desorption95.py | `4a428a2722b047ce7298922dbe71e634e74ed4dcc2bdae66bcc3b55079d5bea4` |
| source.json | `d533f156e287a6772c10e8cea6e686449c2c47bcfb66f4cc26df6b4920349d94` |
| facts.json | `543d55918db7df6d0cc0f695c5dceadbdebda82b83f4fdde206266bcd12f2f16` |
| activity_source.json | `27d89047730b4dd4ffe9d879debaecb1ff9d88f92923a37eafa7038ae2ad484b` |
| codata_source.json | `e8d45b2949e96c6da549030c1f0745f3b522f3d3ee3ab25f7fc95bab316d2714` |

## Resolved finding

[MEDIUM, resolved] The original `_log_enclosure`, line 60 at source SHA `59aa492e2c113f22bf02de641755524ba91783af5ba7c8c647f3ed6041a35d64`, constructed `Context(prec=50)` and therefore inherited unspecified settings from mutable `decimal.DefaultContext`. Setting `DefaultContext.traps[Inexact]=True` made a valid W=.15,95degC lookup raise unwrapped `decimal.Inexact`. The existing current-context test did not cover this application-wide default. `DECIMAL_PROBE.json` preserves the independent reproduction.

The final implementation specifies precision, rounding, exponent limits, capitals, clamp, empty flags and its exact trap set. It retains traps for invalid operations, division by zero and overflow, while allowing the intentional rounded logarithms. The new regression changes DefaultContext rounding/exponents/clamp and both Inexact/Rounded traps. Its genuine pre-fix log records one failure with 36 tests deselected. The combined Arlabosse suite then records **57 passed in 0.29 s** (new 37 plus existing 20), not 59.

The reviewer independently repeated the same full-point comparison after changing every DefaultContext scalar field and enabling every flag and trap; the returned DesorptionPoint was unchanged. All process-local defaults were restored. `FINAL_CHECKS.json` records the result and final hashes.

## Other code conclusions and checks

- Metadata is pinned by a compiled source hash and parsed from the exact bytes verified. All nine required assets are checked on construction and every public operation. Resolved asset paths must remain inside the explicit root; missing or changed evidence fails closed. Reading verified facts from the retained byte snapshot prevents a second unchecked parse read. These guards intentionally require privately cached originals, as declared; repository/wheel redistribution is not assumed.
- Exact input semantics match the API: int/Fraction/finite Decimal are exact, finite floats mean their shortest decimal spelling, and bool/string/nonfinite inputs are rejected. Only the exact 95degC/368.15K isotherm and the nine extracted W nodes are admitted. There is no interpolator or hidden continuous-domain expansion.
- Nine activity readings and six heat readings are retained. Heat at W=.10,.50,.60 remains null with null main bounds and explicit occlusion reasons; the module does not substitute visible-only fragments. Total desorption heat keeps the removed-water mass basis and latent-heat inclusion. Chemical shift is relative J/mol water; it is not added to wet storage or represented as absolute chemical potential.
- The actual registry constructs successfully. Activity traces only to Arlabosse; heat also includes Ferrasse/Lecomte method context; chemical potential traces to Arlabosse, NIST constants and Hack's activity identity. It does not acquire dry-Cp or unrelated heat dependencies. Conditional applicability and unquantified experimental uncertainty remain visible; registry tracing does not admit a material model.
- Arithmetic consumes rational limbs, not display approximations. R is reconstructed exactly as kB*NA and checked against the recorded exact R. Logarithm numerical bounds remain separate from propagated raster bounds and unknown experimental uncertainty. Exact rational numerator/denominator limbs serialize as strings; a returned point passed a strict JSON round trip without losing nulls or qualification flags.

The independent original-image review was read, and its facts SHA matches this module's frozen asset. Its reconstruction and thermodynamic proof were not duplicated; the parallel mathematical/source reviewer owns those conclusions. This reviewer performed only source/asset checks, registry construction, JSON round trips and short discrete-lookup probes. No dependency installation or physical-engine run occurred. `git diff --check` passed.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — final discrete-source code only; the initially reported MEDIUM context defect is resolved and preserved in review evidence.
