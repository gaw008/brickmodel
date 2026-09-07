# Independent review: depletion component work and energy binding

Verdict: **APPROVE**. No actionable findings in the isolated three-production-file candidate. Repository production source/tests and candidate files were not modified by this reviewer. This approval concerns accounting/identity propagation, not a deforming-solid host or a material model.

## Reviewed behavior

Read full relevant ordinary, observe, terminal, compare and commit paths plus both wrapper evaluation changes. Ordinary callbacks and terminal/refinement observations share a fixed component schema, including after mode changes. Every ordinary stage and explicit observation verifies the initial energy identity; terminal Euler state construction and the root's already-reviewed writeback preserve it. A None map remains None. Initial cancellation does not invent a schema or component ledger.

Terminal components use Fraction(endpoint)-Fraction(start), multiplied by each represented rate before a single binary conversion; the signed per-component conversion error is retained. Main work, faces, inventories and components therefore refer to the same actual terminal panel. Component decomposition residual is separately accumulated as the sum of its per-panel absolute value, using the existing energy absolute tolerance. All path panels are checked before any global times/states/modes/corrections/prefix counters are committed. Discarded previews do not contaminate accepted component totals.

The two wrappers forward the map unchanged while retaining their original face/source behavior. Their tests instrument actual evaluate methods with controlled collaborators and bypass constructors; these prove wiring, not real EOS, constructor source admission or future total-energy-host compatibility. The candidate leaves those constructors unchanged. Large cancelling component truncation errors are not certified merely by passing the net-energy estimator; that limitation is accurately stated in the candidate README.

Candidate integration.py and depletion_roundoff.py compare byte-identical to the root repository versions containing the generic identity work. Their hashes are bound below. No unexpected production difference was found outside the three intended candidate files.

## Independent tests and additional probes

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/brick-depletion-components-candidate/candidate:tests/sandbox .venv/bin/python -m pytest /private/tmp/brick-depletion-components-candidate/tests tests/sandbox/test_depletion_integration.py -q --junitxml=docs/sandbox/research/depletion-component-work-independent.xml
```

Actual: **25 passed in 0.64 s**, exit 0; no water EOS. These include fourteen new cases and eleven original manufactured depletion cases, exact subnormal component error retention, schema changes, cross-segment and whole-event budget failures, cancellation and identity preservation.

Independent additional rational probe used a tagged one-cell evaporating oracle with time-dependent cancelling components `q=.17+.03*t` and `-q`, plus nonlinear body power `U-599`, program nodes .05/.15 and tightened ordinary numerical settings. It completed through the event to .2 s with **29 rejected trials and 1573 observations**. Every observed/accepted state retained the tag. Terminal exact dt was `7616996750131/72057594037927936` s; independent Fraction reconstruction exactly matched its elastic component quadrature error. Reconstructed cumulative absolute component residual was zero and matched the returned counter. This exercises actual rejects and a nonconstant terminal coefficient, not only the author's constant-power test.

A separate schema-change-on-dry probe failed with `component_work_schema_changed` after **19 committed steps**, last t=`0.09904970943927764`, zero accepted events/corrections and original wet mode. All committed species prefixes and absolute component counters were independently reconstructed from accepted ledgers using Fraction and matched the result. Tags remained unchanged. Initial versions of this review probe accidentally used unsupported component keys `a`/`b` and correctly failed at the initial state with `invalid_component_work_keys`; after correcting the harness to registered `elastic`/`pore`, the intended post-event failure was exercised. This is reviewer harness history, not a candidate regression.

The baseline probe was independently rerun in both the candidate and the preserved baseline package subprocesses. Their outputs were byte-identical, SHA256 `a33c9048ac03cac4f5747b8fa8a0c4a3ec5955004d5c742d81b1d60c9ffcb8ae`, and their parsed contents matched both persisted baseline.json and candidate-final.json. The comparison covers original None-mode times, state arrays, event times, per-step exchanges and evaluation/rejection/panel/refinement counts; wall timing is excluded. It is a bounded baseline example, not all-model equivalence proof.

## Artifact binding

| Artifact | SHA256 |
|---|---|
| `/private/tmp/brick-depletion-components-candidate/candidate/sludge_sandbox/depletion_integration.py` | `d777acbd443cf4af6ed1ca7f5074fe6a9388cac4691a0e961f9ef238091e8469` |
| `/private/tmp/brick-depletion-components-candidate/candidate/sludge_sandbox/water_phase_transfer.py` | `208141aab520492fb85a6e91f4270f59978418d8fb3f1b24fb254475a36c42a6` |
| `/private/tmp/brick-depletion-components-candidate/candidate/sludge_sandbox/programmed_solid_fluid_heat.py` | `915c9e85ac64b93a2ee0a89d80427acf5d9bed69bf2737bfbc3224fe0663713a` |
| `/private/tmp/brick-depletion-components-candidate/candidate/sludge_sandbox/integration.py` | `cedefb0c3af415be8d9a7fb165c1d2288249b354666567191bbf57c33d405b50` |
| `/private/tmp/brick-depletion-components-candidate/candidate/sludge_sandbox/depletion_roundoff.py` | `65b53e7a9f94b651e5dbc833054b637129ff659b63a290e0512154f3f9333148` |
| `/private/tmp/brick-depletion-components-candidate/tests/test_wrapper_components.py` | `b3ab52d6e0cee85cbf36ef63bf296d93e8ab8b3bed2834d3f6b0f9a05263268f` |
| `/private/tmp/brick-depletion-components-candidate/tests/test_depletion_components.py` | `18a06ce83a0141cf4ba957fa95d71b892244e73872321a919e8c5d04a4a1809c` |
| `/private/tmp/brick-depletion-components-candidate/baseline.json` | `a33c9048ac03cac4f5747b8fa8a0c4a3ec5955004d5c742d81b1d60c9ffcb8ae` |
| `/private/tmp/brick-depletion-components-candidate/candidate-final.json` | `a33c9048ac03cac4f5747b8fa8a0c4a3ec5955004d5c742d81b1d60c9ffcb8ae` |
| `/private/tmp/brick-depletion-components-candidate/README.md` | `9cd24f64a9b8bc89617f814a6f64b67d286aad44eede7806163c33379bf1aa1a` |
| `/private/tmp/brick-depletion-components-candidate/manifest.json` | `cb8de7203a8ea12b8d485753c81fd8b3d071716707ec281fd2e198b32031931d` |
| `docs/sandbox/research/depletion-component-work-independent.xml` | `3a295eb3e3c6462de0e6f789e1c9d6d960d0b341f177b4bdcedd0c69642b97d8` |

## Review Summary

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 0 | pass |
| HIGH | 0 | pass |
| MEDIUM | 0 | pass |
| LOW | 0 | pass |

Verdict: APPROVE — independently verified accounting and opaque-identity propagation; no real wet/deforming-solid integration or physical parameter admission is implied.

## Application verification supplement

After root application, independently compared all three production files and both new tests byte-for-byte against the reviewed isolated candidate: all identical. Parsed `depletion-components-applied-tests.xml`: 38 tests, 0 failures/errors/skips, 0.934 s. This is root-run application evidence, not a second independent 38-test run. No EOS or full-suite rerun was performed.

- `src/sludge_sandbox/depletion_integration.py` SHA256 `d777acbd443cf4af6ed1ca7f5074fe6a9388cac4691a0e961f9ef238091e8469`.
- `src/sludge_sandbox/water_phase_transfer.py` SHA256 `208141aab520492fb85a6e91f4270f59978418d8fb3f1b24fb254475a36c42a6`.
- `src/sludge_sandbox/programmed_solid_fluid_heat.py` SHA256 `915c9e85ac64b93a2ee0a89d80427acf5d9bed69bf2737bfbc3224fe0663713a`.
- `docs/sandbox/research/depletion-components-applied-tests.xml` SHA256 `1e25b2d36a5533bea947c22b7344079967d7788e5e79c5e15017e9963886a573`.
- `docs/sandbox/research/depletion-component-candidate-history.zip` SHA256 `db3b7703a89197eae3ed4be0ddb262f026f03c34148dcdf23b5218c93c8b6d0b`.

The preserved history ZIP has no __pycache__ entries; its candidate production bytes also match the applied source. APPROVE remains unchanged. The ongoing full suite is outside this supplement and no result is inferred before its completion.
