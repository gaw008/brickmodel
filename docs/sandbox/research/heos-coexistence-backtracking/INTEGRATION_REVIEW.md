# Applied Python integration review

Verdict: APPROVE for the applied numerical-control and provenance binding diff. No new CRITICAL or HIGH defect found. This approval does not assert the installed coupled depletion case or full regression has passed.

Read-only review of the actual Git Python/JSON diff, complete surrounding kernel and wrapper, new scripted test file, frozen candidate review and implementation record. No native EOS, tests, installation, production edits or Git mutations were performed by this reviewer. The only reviewer write is this report.

## Independently checked bytes and source links

- Applied kernel SHA-256: `88bbbdd91fbe12d351faf6415883c177fec2fec4a7e51d77d98d864b49d51d93`. Byte-identical to the frozen candidate.
- Approved manifest SHA-256: `ffb53b365cf8e77222b9384403fe4670029f94e7ac46df28a786ad03031f4bf0`.
- Wrapper SHA-256: `763837050119a98f99653449d3d56d3d45c24f7b152cee4d383e867198be6afe`.
- Applied test SHA-256: `dc5451df88a5595839f870be60208637b1817a0d7299a65bc0d0985ce239e11e`. Byte-identical to the candidate's 11-case scripted test file.
- Compared the manifest with `production-before`: only `adapter_sha256` differs. Native runtime files, native git/version, fluid definitions and configuration are unchanged.
- Compared the entire wrapper text with `production-before`: replacing its previous approved manifest hash with the current hash reproduces the applied file exactly. No API or physical-reference changes.
- Source JSON's approved-local-manifest hash equals the actual current manifest bytes. Its actual Git diff contains only that hash change.
- AST parsing of all three Python files succeeded. Ruff, mypy, pylint and black were unavailable on PATH and in both the project and probe virtualenv bin directories; no packages were installed to obtain them.

## Numerical and API assessment

The pre-existing two-equation Newton Jacobian is unchanged. At fixed temperature, Gibbs derivative with respect to log density is the pressure derivative with respect to density; the pressure row retains density factors. The new merit uses the original pressure and Gibbs absolute gates. Acceptance requires both original gates or strict decrease of the largest normalized residual. Accepted densities and their EOS tuples advance together, while rejected trials leave the accepted state untouched. The subsequent outer-state convergence check still requires both gates.

Eight outer evaluated states and at most six trials per unsuccessful transition give a finite maximum of 43 coexistence EOS pairs before successful final snapshot work. No ninth outer state is computed. Failure to find improvement is an explicit WaterNumericalError; invalid trial branches, native responses and stable-slope failures remain fatal, with imposed phase reset in finally. No altered physical constants, reference state, h/u/s corrections, mass/energy reset or increased residual tolerance was introduced.

The helper remains reachable from public saturation/state operations only within the existing transaction lock and source/configuration checks. Accepted EOS tuples are reused within this single transaction; this introduces no cross-call cache or new shared state. Snapshot construction refreshes the native state for each accepted density and retains final physical checks. Diagnostics add trial records under the same existing lock. Wrapper source identity incorporates the changed manifest/kernel and wrapper hash, and the original manifest reread consistency check remains intact.

The added scripted tests cover full-step success without duplicate evaluation, half-step rescue, bounded unsuccessful search, invalid native response and slope propagation, initial and trial branch failures, unchanged full Newton step cap, each absolute convergence gate and outer iteration exhaustion. These are deliberately nonphysical control stubs; they do not establish thermodynamic accuracy. Native-grid, derivative, installed identity, coupled original-failure and full-suite evidence remain separately required and root-owned.

## Scope limits

The enclosing solver was already long, untyped and compactly formatted before this diff; this review does not claim those inherited style choices have been refactored. The change is intentionally localized to a numerical bug fix and its explicit implementation identity. Backtracking improves particular convergence failures but is not a global convergence proof or evidence of source-qualified sludge material behavior.
