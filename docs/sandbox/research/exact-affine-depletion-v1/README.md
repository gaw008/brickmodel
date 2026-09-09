# Exact affine depletion accounting

Baseline: 0c53982. This phase adds a separate exact-time selected-cell affine root enclosure and paired liquid/vapor writeback; it does not replace the existing event integrator.

`exact_affine_depletion.py` frozen SHA256: 8448d3196084116b4b80c5348c48692665017490f969b2b94f505c7bb8601548. Tests were copied with only the fixture path changed to tests/sandbox/fixtures/exact-affine-depletion-v1/saved-cell2.json. No loader is needed in the permanent suite.

Source verification: 93 passed in 4.97 s, covering exact affine depletion, existing roundoff/affine clock, exact clock and exact integration. Installed noneditable verification: 54 passed in 0.18 s, covering exact affine depletion and existing roundoff/affine clock. 71 actual installed modules match source. See saved logs and identity. No EOS calls were made.

Both independent reviews approve this selected-cell numerical helper. The original saved cell2 failure still refuses under the old clock. The new adjacent dyadic enclosure needs 26 refinements and achieves represented correction/gross evaporation ratio 9.226387713494241e-9 under the unchanged 1e-8 gate. The source observations remain the original saved affine samples; this is not a new coupled trajectory.

Each signed component is integrated exactly then rounded once; evaporation uses its positive part rounded downward. All original local, absolute, fraction and cumulative budgets remain. Evidence is validated before a zero-liquid no-op. Explicit source labels are not provider authentication. The test raw state is an accounting fixture, not the full saved physical panel.

Required next integration: whole-state panel positivity and accounting, strictly ordered competing roots, wet-mode switch and mixed RHS with the same exact clock, original full-state comparison gates, atomic packet commit and explicit records/resume. Original four-cell failure, spatial convergence, material evidence and full firing requirements remain unresolved. RESULT.md contains the bridge contract; archives preserve initial test failures and candidate history.
