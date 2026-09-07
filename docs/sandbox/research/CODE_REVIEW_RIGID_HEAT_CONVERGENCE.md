# Independent review: rigid heat convergence

Reviewed 2026-09-07 UTC. Scope: `experiments/sandbox_validation/rigid_heat_convergence.py`, its preregistration/results document, full JSON, and injected failure smoke JSON. No core edits or repeat core approval are implied. Staged diff was empty; relevant benchmark files were untracked during review. Other dirty files belong to concurrent work and were not modified.

## Binding and scope

Approved script SHA-256: `d2d75d19968c547cffaa68237e83a0e37129848f2b7fa6f8c5930c3e46b50a55`.

All nine current source file hashes equal both before/after maps in the full artifact. The document prefix before `## 首次实测结果追加` hashes exactly to recorded preregistration `b9fde6c7931a638d144480666ff59b04544c854079ad529e5b04a2adeafd9fe0`. The appended results do not change the registered thresholds. This verifies preserved bytes, not an independent timestamp authority. Git HEAD is explicitly not asserted to bind uncommitted files.

The benchmark calls actual `GasHeatModel` and `integrate`; no substitute ODE is supplied to the integrator. The manufactured constant-cp gas, disabled matter transport, fixed geometry, and closed adiabatic boundaries consistently reduce that model to finite-volume conduction. This approves evidence for that rigid gas limit only, not wet sludge, phase change, sintering, shrinkage, stress or a real material pack.

## Independent checks executed

Read the full script and relevant model assembly / accepted SSPRK2 ledger call sites. Independently reconstructed initial cell averages by integrating the cosine over each cell (difference of sines), the continuum decay, and the discrete Neumann cosine eigenvalue. Decoded saved energy using the explicit manufactured caloric relation without calling the tested thermal inverse.

Recomputed all seven artifact maximum errors and orders:

- Space: `1.967057054022806`, `1.9917563002019627`.
- Time: `2.011997673908532`, `2.0059924221459196`.
- Finest space error: `0.0006575904075134531 K`.
- Half-time-step finest-space error: `0.0006575698376991568 K`.

Actual saved time/state counts match 100/100/100/200/4/8/16 accepted steps; evaluation counts match `1 + 7 * accepted_steps`. Zero rejected trials and actual step-length gates protect the fixed-step interpretation. Time comparison uses the discrete mode, so spatial error does not contaminate its order. The separate finest-grid time-halving check bounds time contamination of the spatial series.

For every saved step, independently applied the two actual half-step SSPRK2 scalar amplification factors `1-lambda*h+(lambda*h)^2/2`, using rounded saved endpoints. Reconstructed each accepted face integral with scalar stage weights `h*q*(1-lambda*h/2)` and compared with saved face energies. Maximum differences: scalar temperature `5.638867150992155e-11 K`, face integral `9.402878475839316e-11 J`. These are independent review comparisons, not replacements for preregistered pass thresholds. Exact `Fraction` arithmetic on every saved step/cell gave maximum local energy ledger residual `1.4883927423881005e-15 J`, below the unchanged `1e-8 J` gate. Script additionally checks all-time global totals, whole-run cell balance, unchanged inventories, zero boundary flux, and absent reaction/work.

Resource gates and units are appropriate for the recorded platform: per-case 120 s, total 360 s, 512 MiB peak RSS; macOS bytes and Linux KiB are distinguished. Original full artifact reports 8.52169 s and 40.625 MiB. These are observed resource metrics, not a hard OS-enforced memory cap.

Executed actual fresh smoke:

```sh
PYTHONPATH=src .venv/bin/python experiments/sandbox_validation/rigid_heat_convergence.py --smoke --output /private/tmp/rigid_heat_review_resume_20260907.json
```

Exit 0, completed, 2 accepted steps. Repeating the same output path exited 2 before execution with an explicit preservation error. Exclusive file creation also protects the write-time race.

Independently reran the documented failure injection after actual integration, replacing only returned status/reason. Output `/private/tmp/rigid_heat_review_failure_20260907.json` is failed; `main` returns 1 and `core_completed` is false. The existing failure artifact makes the same explicit injection claim and remains unchanged. This checks propagation, not a naturally occurring physics failure.

## Findings

No actionable issue above the review confidence threshold within this bounded benchmark. No need to rerun all seven cases: current source binding matched, saved trajectories and face integrals were independently recalculated, and the live model and failure path were rerun.

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — rigid-gas conduction numerical convergence evidence at the source hash above; full Goal completion is not established.
