# Arlabosse95 discrete runtime: independent source/physics/code review

Runtime verdict: **APPROVE for discrete 95°C source-node lookup and relative molar chemical-potential shift only**. No remaining CRITICAL/HIGH correctness issue was found in the final code below. The MEDIUM replay-documentation issue was fixed and closed after the current README and actual portable-replay log were reviewed.

Final reviewed runtime SHA-256: `a197a22c095c87f4e388b86c648b7cdcd18cbf75eed34575e10ca09f347137f8` for `src/sludge_sandbox/arlabosse_desorption95.py`.

Final reviewed test SHA-256: `4a428a2722b047ce7298922dbe71e634e74ed4dcc2bdae66bcc3b55079d5bea4` for `tests/sandbox/test_arlabosse_desorption95.py`.

Source manifest SHA-256: `d533f156e287a6772c10e8cea6e686449c2c47bcfb66f4cc26df6b4920349d94`. Preserved facts SHA-256: `543d55918db7df6d0cc0f695c5dceadbdebda82b83f4fdde206266bcd12f2f16`.

Scope included the runtime module, its tests, and `data/sandbox/research/arlabosse95/` and `docs/sandbox/research/arlabosse95/`. `git diff -- '*.py'` was read; concurrent CLI/local-view/source-study changes were explicitly left outside this review. No production files, source assets, or frozen facts were modified by this reviewer. Private asset mutation checks used copies under `runtime-review/isolated-assets/`.

## Validated behavior and physics

The nine discrete moisture levels are exact source-node lookups. All source activity values/bounds and available heat values/bounds were independently compared against the original frozen facts. No interpolation, neighbor snapping, heat-gap filling, or temperature extrapolation occurs. Different accepted input representations give the same result, with the float-shortest-decimal policy explicitly declared; exact binary Fractions remain distinct.

All nine activity values can produce a source-derived activity shift. The three unavailable Figure 2 heat values remain null independently of activity readability. Heat remains J/kg removed water including the latent contribution. The relative activity shift remains J/mol water, relative to the activity's own standard potential; it is not an absolute water potential, J/kg energy term, equilibrium-pressure prediction, drying rate, or wet-storage addition. This agrees with the previously independently read Arlabosse/Ferrasse source chain and the Hack 2011 activity identity described in `SCHEME_REVIEW.md`.

Exact decimal SI defining constants are multiplied as Fractions, as is the declared 368.15 K. The numerical formula encloses independently rounded ln(n) and ln(d) before exact rational subtraction and multiplication. Monotonic endpoint propagation gives the reported conditional digitization enclosure. Numerical enclosure and source-raster propagation are separate; the experimental uncertainty remains unknown. All nine shifts are negative, and the numerical bounds lie inside the propagated raster bounds.

The source manifest is hard-bound, every listed asset is rechecked on each call, and the same checked bytes are then parsed. The manifest maps the historical extraction paths to the current private cache paths without changing the frozen facts. Each asset path is resolved and checked against the explicit repository root. Source, original figures, review metadata, activity identity metadata, CODATA metadata, and the original CODATA extracted-text cache are all required. This fails closed if private assets are absent; it does not imply they are shipped with a repository clone or wheel.

The returned physical readings are frozen dataclasses, and converting them to mutable records or mutating a registry payload does not alter a subsequent query. Trace source sets were checked independently: activity uses Arlabosse; heat adds Ferrasse/Lecomte for heat meaning; the relative shift uses Arlabosse, CODATA, and the Hack activity identity. No dry-Cp or unrelated heat dependency was inserted into the shift computation.

## Decimal-context correction and attribution

The first inspected code SHA was `59aa492e2c113f22bf02de641755524ba91783af5ba7c8c647f3ed6041a35d64`. Its `Context(prec=50)` insulated against the active context but still inherited unspecified fields from mutable `decimal.DefaultContext`. Another code reviewer identified this; the parent supplied a failing regression and a fix specifying every context field. This review did not discover that defect and does not claim it did.

The earlier scheme recommendation that `Context(prec=50)` was sufficient isolation was incomplete. Correct final requirement: precision, rounding, Emin/Emax, capitals, clamp, flags, and traps are explicit. The final implementation was reread after the fix, its tests were rerun, and all nine nodes were additionally queried while BOTH DefaultContext and the active context had one-digit precision, all traps/flags enabled, Emax/Emin=0, changed rounding, capitals, and clamp. Results remained identical. The first-version snapshot and checks are retained separately rather than relabeled as final-version evidence.

## Checks actually run

- `PYTHONPATH=src .venv/bin/python -m pytest -q tests/sandbox/test_arlabosse_desorption95.py`: **37 passed** on the final code. The previous 36-test version also passed before the new DefaultContext regression was added. The parent's separate combined result of 57 passing tests was read but is not presented as this reviewer's independent 57-test execution.
- The existing tests compare all nine shift values and activity-bound endpoints to a separate 160-term exact rational atanh-series enclosure. The earlier scheme review independently used a 120-term exact rational series for all 27 actual activities/endpoints, with an explicit tail bound.
- `RUNTIME_NEGATIVE_CHECKS.json`: 25 additional check groups on the first inspected implementation. They include all nine nodes across accepted input/temperature representations, source-fact equality, frozen/result isolation, three exact dependency-source traces, all nine post-construction asset mutations, an out-of-root symlink with otherwise correct target bytes, and a count confirming one read per asset per query. All passed. The final change was confined to explicit Decimal-context construction; these old-version observations retain their original code SHA.
- `FINAL_CONTEXT_AND_DOMAIN_CHECK.json`: final-version all-nine simultaneous active/default-context corruption, eight additional invalid temperature inputs, negative shifts, numerical/raster containment, correct units, and continued qualification refusal. All passed.
- ruff, mypy, pylint, and black were checked on PATH and in the existing virtualenv; none was available. No static-linter success or coverage percentage is asserted. Syntax is exercised by actual successful import/tests.

The first reviewer's pytest command omitted `PYTHONPATH=src` and failed test collection with `ModuleNotFoundError`; the corrected command above succeeded. This was an invocation-environment error, not a production-module failure. The parent's RED/FIRST_RUN/SECOND_RUN/GREEN and DefaultContext regression evidence remain in the separate runtime-evidence directory.

## Resolved documentation finding

[MEDIUM] Archived extraction invocation assumes the old scratch layout

File: `docs/sandbox/research/arlabosse95/EXTRACTION.md:5`

Issue: The archived report still describes `extract_pixels.py NEW_OUTPUT.json` as the replay entry. Running the archived script from its repository location fails because its preserved relative paths expect `docs/sandbox/research/arlabosse-figure1.gif`. The actual original is privately cached at `.tools/source-cache/arlabosse2005/figure1.gif`. `independent_check.py` likewise retains the historical layout. Preserving those exact script bytes is reasonable, but the present archive needs a current replay instruction.

Fix: Add a current README that explicitly labels the preserved scripts/reports as historical extraction artifacts and gives exact commands to rebuild their expected private scratch layout from the manifest's verified assets. Keep the original scripts, facts, and source-review hashes unchanged. No production numerical change is needed.

Resolution verified: `docs/sandbox/research/arlabosse95/README.md` SHA-256 `a5631b80b8972d73683c8512b5c4c8482fbe73421ad44049a43f1303c9f8b457` now explicitly describes the historical layout and gives a complete temporary-directory reconstruction command. The command copies the unchanged archived scripts/protocol and private original GIFs, runs the extractor twice in the same new layout, compares all original/replayed fact fields except explicitly recorded absolute source paths and Python/Pillow/NumPy versions, and runs the independent raster checker. The author's actual `runtime-evidence/PORTABLE_REPLAY.log` was read through its successful final message. It confirms 18 statuses, 119 pixels, and same-new-layout replay equality. The new fact hash differs, as expected from absolute path metadata; the README does not claim byte equality with the historical facts. No repeated scientific study was run to close this documentation issue. The runtime/test/manifest/facts/extraction-script hashes were rechecked and remain those listed above. **Finding closed.**

No other required fix was identified in this bounded review. Continuous moisture-domain admission remains null, and material/full-cycle/training qualification remains false.
