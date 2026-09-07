# Component-work implementation history

2026-09-07, implementation worker `/root/boundary_program`. This file was written retrospectively from actual tool outputs retained in the current conversation. **The transcript observations below are summaries, not preserved raw pytest log/XML files.** No missing log is reconstructed or presented as an original artifact. Independent review and root installation verification have separate records.

## Tests-first and environment observations

1. First command `.venv/bin/python -m pytest tests/sandbox/test_component_work_ledger.py -q --maxfail=1` failed during collection: `ModuleNotFoundError: No module named 'sludge_sandbox'`. This was a missing source-path environment, not the intended feature RED.
2. With `PYTHONPATH=src`, the same test command actually reached the first new test and failed: `TypeError: Rates.__init__() got an unexpected keyword argument 'cell_power_components_w'`. Result: **1 failed in 0.06 s**. This was the meaningful missing-API RED before implementation.

## First implemented run and numerical correction

Command: `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_component_work_ledger.py tests/sandbox/test_integration.py -q`.

Observed first implemented result: **1 failed, 39 passed in 0.49 s**. Accepted-stage component quadrature and prefix checks had passed. The new analytic test used `relative_tolerance=1e-5`, energy scale 100 J and initial/maximum step 1 s; its final represented energy was `1.6645646270548515 J`, versus analytic `5/3 J`, outside the preregistered absolute `0.001 J` final check. The local error-control settings did not imply that global threshold.

The fixture's numerical relative tolerance was tightened to `1e-7`; the physical rate law, analytic solution and `0.001 J` acceptance threshold were unchanged. The production integrator was not altered to fit the analytic answer. Four additional bounded tests then covered cumulative decomposition-roundoff rejection, exact subnormal quadrature-roundoff diagnostics, None-to-component schema changes and multicell signed work.

## Final local verification observed

Command: `PYTHONPATH=src .venv/bin/python -m pytest tests/sandbox/test_component_work_ledger.py tests/sandbox/test_integration.py -q`.

Observed output: **44 passed in 0.51 s** (16 new cases and 28 prior integration cases). No EOS or full-system run was performed by this worker for that command. There is no worker-created canonical XML/stdout artifact for it; this is an observation summary.

Frozen implementation submitted to independent review:

- `src/sludge_sandbox/integration.py`: SHA256 `7316bd04a91c32ed45ea1aa5011b39dd4b6ba3b893b2f49acf1e8cb95ec47a64`.
- `tests/sandbox/test_component_work_ledger.py`: SHA256 `aeb92b6ee2f822a08a2e9e730f78f6474e13655a29e4695d5c5acaadd9bbab2d`.

## Exact qualification

Ordinary `integrate` records only accepted fine SSPRK2 stages, using their actual weights. Exact Fraction diagnostics distinguish each component's product/sum representation error from the difference between represented total work and represented component sum. Cumulative absolute per-cell decomposition residual is limited by the existing energy representation budget; excess stops before committing the proposed step and preserves prior accepted history.

Net-energy adaptivity does not bound the truncation error of large mutually cancelling component integrals. Material identities and physically meaningful decompositions remain the operator's contract. At this checkpoint, depletion terminal panels and wet wrappers do not yet propagate these optional fields. Neither that support nor a complete deforming wet-solid simulation is claimed by the 44-test result.
