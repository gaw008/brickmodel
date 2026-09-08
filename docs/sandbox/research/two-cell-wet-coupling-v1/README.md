# Two-cell wet reaction and transport evidence

This archive records a manufactured two-cell integration experiment using source-qualified pure-water properties, manufactured solid A/B reaction and skeleton/transport coefficients, and prescribed deformation. It does not qualify raw sludge, free sintering, material strength, or a full firing cycle.

Production source/test baseline: `67730b2`, unchanged during this phase. All 43 actual installed modules matched the source after execution. The previous 1279-test suite belongs to that unchanged baseline; it was not rerun for this evidence-only phase.

Four trajectories completed: coupled/control each with 2 coarse or 4 fine accepted steps. Every saved prefix passed independent species/element/energy ledger checks. Two initial callbacks each passed 63 independent gas/transport/heat algebra checks. Six supervisors terminated; 180 inputs per callback and 181 per trajectory matched before/after/current bytes. See `actual-run-verification.json`.

`four-run-comparison.json` contains raw differences, fixed thresholds, decoding bounds and source/ledger bindings. Both cell temperature effects (approximately +1.4464e-6 and -1.4464e-6 K) and energy effects pass the preregistered empirical resolution indicators. Water inventory effects remain below the amount threshold; phase-rate differences remain unresolved without a certified sensitivity interval. These screens do not certify global ODE error, continuum convergence or material accuracy. Algebra tolerance was frozen after the first coupled callback pilot, before control callback and all trajectories; the record does not claim earlier preregistration.

## Contents and reproduction

`original-evidence.zip` retains all 51 raw files: frozen experiment scripts/PLAN, actual results, supervision records, independent audit/comparison scripts and outputs, installed-module evidence and reviews. `manifest.json` lists each exact byte count and SHA-256. All entries were reopened and checked after writing. Hash verification proves archive identity only.

Readable PLAN and independent review reports are under `readable/`. The next fixed-domain spatial experiment is specified in `readable/two-cell-audit/NEXT_SPATIAL_SCOPE.md`; q(N), interface area, phase coefficient and inventories must scale consistently. Two grids alone do not prove spatial convergence. No new spatial trajectory was executed in this phase.

The frozen scripts use the recorded workspace and isolated Python environment paths. To replay on another machine, extract into a new directory, remap paths explicitly, install the locked package/water dependencies, regenerate its declared source snapshot, and preserve both original and new identities. That relocated workflow has not been verified. On the original paths, launch callbacks and then wet runs sequentially using the saved `run.py`; existing result filenames are intentionally refused. Never overwrite these evidence files or call replay against a live attempt.

Independent audits use only saved JSON and the standard library: `audit_callback.py`, `audit_ledgers.py`, and `compare_runs.py`. Their exact arguments and output bindings are retained in the scripts/results. Do not confuse arithmetic replay with an independent thermodynamic or external experimental oracle.

Remaining full Goal requirements include a complete raw-sludge material evidence package, free sintering/cooling, public validation of three required mechanism groups and held-out conditions, integrated CLI/UI and multigeneration search. The known ordinary integration program-knot failure at .005 remains separate and unresolved.
