# Independent source programmed boundary and surface extraction review

Scope: six files in FINAL_FREEZE.json, source changes read completely and compared with HEAD snapshots saved before authors edited. No repository edits by reviewer. No native EOS experiment or full suite.

## Surface extraction

Original surface arithmetic, residual summation order, tolerance scale, endpoint/root update and exception type preserved. Existing wrapper still resolves the current transport when passed, and calls its actual _face_metric and _conduction; this retains slab, spherical and moving geometry dispatch. SurfacePolicy is imported unchanged. The public numerical kernel documents that the caller must supply a finite continuous monotone conduction callback, valid geometry and source-bound coefficients; it is not a material model. Real wrappers provide that contract. Existing observation and identity golden assertions pass.

## Programmed source boundary

Exact SourceWetColumn/ExactProgramView/BoundaryProgram/SurfacePolicy types are bound, along with all geometry, coefficient and program identities; runtime checks precede base evaluation. Gas-temperature program domain is checked against all caloric curves. Base is evaluated once. Exterior gas face has zero conductivity, avoiding a second direct gas-to-cell heat path; two quarter distances form the outer half-cell. Film/radiation root supplies surface-to-cell conduction. Outward energy is gas diffusive and donor advective enthalpy minus that inward conduction; radiation/convection are diagnostic components, not additional energy sources. Shared gas face guards retain curve/basis/mass/R requirements. Outer face adjacency is final cell to exterior, left boundary stays closed, internal rates are reused.

## Integral extension

Default closed dataclasses and behavior remain, including complete run golden excluding elapsed time. Exact origin and duration/steps define nominal endpoints. Program breakpoints are strictly internal, sorted by existing ExactProgramView; coincident nominal/program endpoints are consumed once. Both midpoint stages use exact Fraction times; full step starts from old accepted state. Endpoint evaluation completes before state/ledger append. Added boundary ledger records exact component balance defect separately from represented root residual and tolerance; it does not add another heat. Arithmetic budgets are still numerical bookkeeping, not time truncation or physical fit bounds.

Actual verification: 19 passed in 7.67s: five reviewer checks, seven shared surface tests, seven programmed-source tests. Independent checks: linear cooling resistance and positive outward sign; zero conductivity retaining open-gas enthalpy; 10^18 translated exact start inside domain with nominal endpoint equal to knot and no duplicate/zero step; cancellation before final observation discarding whole candidate; changed source rejecting before base evaluation. Supplied tests additionally exercise varying exact program interpolation, N3 inflow/outflow donor policy, open global energy/species/water ledger, one base call, source/domain refusal and complete accepted prefix. Logs/tests in this directory.

All six Python files parsed successfully. Ruff/mypy unavailable in reviewer runtime; no lint-clean claim. Frozen surface three-file hashes matched author manifest. No unresolved critical/high functional defect identified; approve the exact reviewed bytes. This remains manufactured geometry/transport with source-limited dry caloric and conditional fluid numerics, not complete firing or material validation.
