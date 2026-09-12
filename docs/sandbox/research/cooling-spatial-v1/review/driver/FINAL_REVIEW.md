# Cooling spatial driver: independent final code review

Decision: **APPROVE** the reviewed driver for the already registered execution. No remaining correctness blocker was found in this bounded review. This decision is not a spatial convergence result or material/scientific validation.

The final identities are recorded in `FINAL_IDENTITIES.json`:

- `run_spatial.py`: `91c8b4b188531a03add821fe95330653d49489d2d0b0549094523b61d6a8004b`
- `supervise.py`: `b049c431c6c71bdaebfaeb758fda7784a44b74e424edaa756c4b00bdd0189b23`
- `test_spatial_driver.py`: `d93d5c3cbed1379f90fca3c12e48117c0120d85035a27bce894921c04e4c34c5`
- `NEXT.md`: `dfa6363b6e83d0a2de8495153ce81c7a814ee55901d54a43f84f790baa7872fb`

## Fixed blocking finding

[HIGH, resolved] A failed post-child source read discarded the supervision terminal record. In the original supervisor `37e028a4…`, an injected second `hashes()` call raised `FileNotFoundError` after a fake child returned exit code 7 and saved one coarse accepted record. `START.json` and that accepted record remained, but `EXECUTION.json` did not exist. `RED_POSTHASH.json`, `supervise-red-snapshot.py`, and `red-posthash/` preserve this evidence without changing the source or launching a process.

The final supervisor catches post-child hash/prefix/worker-result read errors, retains the actual return code and reaping status, records unavailable evidence explicitly, saves readable accepted prefixes, and makes `passed=false`. Independent regressions also cover an invalid UTF-8 prefix and a valid JSON result that is not an object. All three now preserve the terminal JSON. No old failure evidence was overwritten.

## Equations and numerical evidence

Differentiating `A(T) r = K T`, with `A = diag(C−2bT)+2bT wᵀ`, gives `A J = K−2b diag(mean(r)−r)`. The implemented heat rows are `V K`; differentiating `2Vb(mean(T)−T)mean(r)` gives the implemented work rows. The face entropy term `G(T_i−T_j)²/(T_i T_j)` yields the implemented two signed derivatives. Columns for already accumulated heat, work, and entropy are zero.

The independent tests compare this complete matrix with directional finite differences of the actual candidate's augmented outputs at six off-trajectory manufactured states/directions spanning N=16,32,64. Both difference steps and the Richardson combination are used. Each T/Q/P/S block is additionally checked against its own maximum derivative, so the approximately 1e−11 common-direction power derivative cannot pass through a temperature-sized absolute floor. The largest observed block-relative difference is 1.727e−7 for this tiny power block; `JACOBIAN_BLOCK_ERRORS.json` preserves all 24 block results. These are point evaluations, not the registered initial trajectory or a time integration.

The actual local SciPy `BdfDenseOutput` implementation was inspected; its source file has SHA `92014c6ddb85e0757ae2b951dfd783a4b5b92a9829a5cdf3f26b41c8390fe4b7`. Its stored `t_shift`, `denom`, and `D` agree with the driver's Newton-polynomial interpretation. Each interval operation rounds outward; the additional 64u magnitude allowance covers the short binary64 cumulative-product/dot evaluation in the registered finite domain. Five independent Fraction-arithmetic tests enclose the stored polynomial over each whole closed segment for orders 1–5, with signed coefficients and nontrivial shifts. Separate 49-point checks exercise the actual SciPy evaluation path; those samples are not the whole-interval proof. The author tests also exercise an interior overshoot with admissible endpoints and a failed segment that preserves the prior confirmed prefix.

## Control flow and scope

Static review confirms the fixed parameter set, exact cell-average initialization and separate discrete initial energies, full augmented BDF tolerances, one deadline shared by both accuracy policies, actual candidate stress matrices, separate accepted-step and 101-sample records, local/global/entropy gates, and explicit failures. Dense-domain uncertainty is rejected before confirming the new endpoint. Single-grid completion does not claim cross-grid validation; material qualification remains false. The raw RHS residual maxima are labeled separately from the integral/domain gates, as registered.

`independent-final.xml` confirms **14 passed, zero failures/errors/skips, 0.277 s** using the existing repository Python environment. The previous independent run is retained. `ruff`, `mypy`, `pylint`, and `black` were checked and are unavailable; none was installed. The new subject files are untracked at review time, so `git diff -- '*.py'` does not display their contents; they were read directly and hashed.

No production code, author driver/test, protocol, installed environment, or old evidence was modified. No formal spatial integration, prior cooling trajectory, optimizer, or water EOS was run. The cross-grid comparison program and eventual saved execution data are outside this code-review decision. Failure of the output filesystem itself cannot be represented as a successfully saved terminal record.
