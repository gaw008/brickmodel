# Fixed-domain spatial refinement evidence

Two-to-four cells at the same .02 m half-slab and .01 m2 reference face area. Actual source-qualified water properties are combined with manufactured A/B reaction, phase conductance, skeleton and transport, and prescribed deformation. This is not a raw-sludge material package or a full firing cycle.

## Verified scope

- Actual installed skeleton API scaling: 171 checks plus six deliberately wrong-weight negative controls, with an independent exact interface-energy formula. No EOS in that check; phase/reaction dimensional statements there are analytic only.
- Before native execution, code review found an intermediate fluid template pore volume too large for refined cell geometry. The minimal correction scales that construction template. Actual evolving pore volume is still recomputed from bulk minus solids. Original candidate/PLAN are preserved in the raw ZIP under spatial-experiment/preflight-original.
- Gradient and uniform four-cell callbacks completed in4.741476/4.654432 s; each passed144 independent gas and three-internal-face arithmetic checks. Conservative initial parent-pair N/E sums are exact. Same-temperature parent-versus-child forward energy discrepancies are zero, within documented full storage bounds. Uniform evidence is initial-state only, not uniform trajectory parity.
- Four-cell gradient coarse/fine time trajectories completed in30.990010/55.240541 s with2/4 accepted steps. All saved-prefix species/element/energy ledgers pass. Per-cell extensive tolerances were halved; original global tolerances were retained. Maximum local species/energy discrepancies are9.31892e-17 mol and1.90234e-11 J.
- Four supervisors are terminal. Callback181/wet182 source inputs each match before/after/current. All43 actual imported installed modules match source. Production/test baseline67730b2 remained unchanged; its existing1279-test evidence is in the earlier affine-terminal archive, not a newly rerun suite.

## Spatial result remains unresolved

`grid-comparison.json` compares conserved parent-pair sums against the exact-source two-cell results archived in `../two-cell-wet-coupling-v1/`. Fine-time grid energy differences are about±1.44955e-5 J; within-grid time-cap changes are at most8.73115e-11 J. Temperature is only a reference-volume-weighted diagnostic average: grid differences are+1.44639387e-6/-1.44640256e-6 K, versus cap differences no larger than5.79803e-12 K.

The initial condition is piecewise discontinuous. The central face transfer distance halves on refinement, so initial heat/diffusion flux doubles; do not tune coefficients to erase this. These two spatial samples and the15.258789 microsecond interval do not prove asymptotic spatial convergence. No artificial mesh PASS threshold is imposed. Temperature averages are not thermodynamic temperatures decoded from aggregate energy.

## Evidence and replay

`original-evidence.zip` preserves43 raw files, exact experiment scripts/PLAN, results, supervision logs, original preflight candidate, auditors/comparator, scaling output and reviews. Every ZIP member was reopened and compared to its SHA-256/length in `manifest.json`. Hashes prove identity, not physics. Selected JSON outputs are copied byte-for-byte next to this README; plans/reviews are under readable/.

Scripts retain original workspace and isolated Python paths. Original commands were sequential `run.py callback callback-4-gradient-attempt01 --cells 4 --profile gradient`, then the analogous uniform callback, followed by `run.py wet wet-4-gradient-0-attempt01 --cells 4 --profile gradient --refinement 0` and refinement1. The saved launcher invokes the recorded installed Python and freezes source inputs. It refuses existing results. Replay into a new directory with explicit path/snapshot updates; do not overwrite this evidence. Relocation to another machine has not been validated.

Saved-JSON-only `audit_faces.py`, `audit_ledgers.py` and `compare_grids.py` preserve their original input bindings and error gates. The coarse two-cell run data needed by comparison remains in the preceding archive and original recorded directory.

The next bounded numerical investigation is `readable/spatial-audit/NEXT_NUMERICAL_PRIORITY.md`: reproduce the retained ordinary program-knot residual failure, then fix endpoint selection without skipping time or loosening midpoint guards. Its source-level diagnosis is not yet a executed regression or implemented repair. Full raw-sludge evidence, free sintering/cooling, public three-mechanism/held-out validation, CLI/UI and multigeneration search remain required and incomplete.
