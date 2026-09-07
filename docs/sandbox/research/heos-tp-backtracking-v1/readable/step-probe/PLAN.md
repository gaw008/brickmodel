# Six-fraction TP native step diagnostic: preregistered plan

Prepared against repository commit `9ab4b659c539dcc790e4286c241a92016f9de670`. Preparation performed AST parsing only; no provider import, native EOS call, tests, install or production changes. Execution requires independent parent review. This experiment cannot establish accepted material physics, a host state, a solver repair, or completion of the wet reacting model.

## Fixed evidence and hypothesis

The unchanged exact-point public provider failed with `heos_tp_not_converged`; all eight rows matched the captured full replay. Inputs are reconstructed solely from captured float hex: T `0x1.2700000000000p+8` (295 K), P `0x1.a379187ce8000p+15` Pa, phase liquid. This temperature is the host inverse bracket lower endpoint, not an accepted brick temperature. Two repeated densities differ by 417 ULP; no adjacent-float or fundamental-resolution claim is warranted. Copied source snapshots and their original paths/hashes are in input-manifest.json.

Hypothesis: one of six fixed fractions of the original first Newton step may yield a directly evaluated residual below the ORIGINAL density-dependent gate. Fractions are exactly 1, 1/2, 1/4, 1/8, 1/16, 1/32, all from the same captured first density, never chained. No adaptive extension or extra fractions are permitted.

## Native operations and guards

Load the installed public approved HEOS provider using repository water data and heos-8.0.0-approved-manifest.json. Constructor work retains existing source/native/configuration qualification. Require installed Python modules byte-identical to repository copies and the captured kernel identity. Use existing provider._guard before/after and existing kernel._transaction with its lock and pre/post configuration/fluid checks. These are diagnostic uses of actual private APIs, not a new provider interface.

Within that transaction use original temperature/pressure/phase domain guards, saturation pair and stability checks, original PT flash seed and native phase, then impose the requested phase. Verify seed and every stored first-row native field exactly match captured first evaluation. Preserve positive finite density, saturation branch, original positive finite slope formula, finite residual, and original abs(full log-density step) < 0.1 guard. Every candidate performs its own native DmassT update and records actual h/u/p/slope/residual. An extra explicit phase and finite-record check makes invalid results fatal. No source or native exception is treated as a rejected line-search candidate.

The exact stopping gate remains min(1e-4, rho*1e-7) Pa. Store both actual gate pass and strict decrease in abs(residual)/gate. Decrease alone is never success. Each candidate meeting the gate must also pass unchanged kernel._snapshot (full existing native Table-3 checks) and density branch. These snapshots remain diagnostic records, never returned to a host. Verify full-fraction density exactly matches captured second density. Always unspecify phase. No solver source, manifest, loop iterations, target pressure, host bracket, physical parameters or EOS selection is changed.

Work is bounded by unchanged qualified constructor + one original saturation-pair solve + one PT seed + one base DmassT + six trial DmassT evaluations + at most six unchanged snapshot checks (each may use the separate check state). There are no fixture builds, host inversions, replay, warmups, interpolation or averaged thermodynamic values.

## Evidence, failure and execution

probe.py writes step-probe-result.json atomically, refuses overwrite, records input identities, installed module hashes before/after, active candidate before native evaluation, all completed candidates, captured-base field equalities, verified snapshots, errors/tracebacks and elapsed time. Invalid native/identity/phase results abort and preserve partial evidence. External kill may preclude child JSON; the supervisor still retains attempt command/logs/status, timeout and cleanup evidence. No gate pass is child exit 1; a fully completed diagnostic with at least one verified gate pass may exit 0 and is labelled diagnostic_gate_pass_observed, never accepted physics.

run.py uses the existing process supervisor with a 30-second external cap, unset PYTHONPATH, no bytecode writes, and the existing installed venv. It records all repository/installed sandbox Python files, water inputs, scripts, PLAN, copied evidence/manifest/review and supervisor source. Supervisor success requires status complete AND child returncode 0. No other attempts are authorized by this plan.

After parent approval, exact command:

```
/private/tmp/brick-water-backend-probe/venv/bin/python /private/tmp/brick-heos-tp-step-probe-v1/run.py attempt-01
```

Any successful result only supports later bounded candidate design and independent tests; production changes and full coupled replay require separate review.

## Frozen file hashes

- `TP_FAILURE_NUMERICAL_REVIEW.md`: `7a96a7689e899cbcb910fcb97106325e490bc9ca9026f335c5d79350f74665cc`
- `captured-tp.json`: `dd707eed205fa5162f5fe8c78479bc086dda465f107441161fad25fd1f3929d5`
- `exact-point-result.json`: `027bccf488a0c5100b77302b364ace8084cef9829204e7d89155729c0133e13a`
- `input-manifest.json`: `dbd84a1b3ff22b5f0f95754028d097375fb42679495d5b717f8fc5a82e0a63f9`
- `probe.py`: `179323379e85d4ee9f2ac1eabd486b2b448ff32ff6a152ac1c81542891879d9a`
- `run.py`: `d660d46622a98200786d2e9eaeb6c35c8754cb0738eaf76a3ea5b7a8ad5d4df5`
